import { useState, useEffect, useRef } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ROUTES } from '../../routes';
import axios from "axios";
import "./quiz.css";
import Header from "../../components/header/header";
import Loader from "../../components/loader/loader";
import { CircleCheck, CircleX } from "lucide-react";
import userManager from '../../utils/userManager';

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:5000";
axios.defaults.baseURL = API_BASE;
userManager.applyAuthHeader(axios);

// 通用选项标准化，放在模块顶层以便 QuizPage 与 Question 共享
const normalizeOptions = (q) => {
  if (!q) return [];
  const opts = q.options;
  if (!opts) return [];
  if (Array.isArray(opts)) return opts.map(o => typeof o === 'string' ? o : String(o));
  if (typeof opts === 'string') {
    const lines = opts.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
    if (lines.length > 1) {
      return lines.map(l => l.replace(/^\s*([A-Za-z0-9).-]+)\s*/, '').trim());
    }
    const parts = opts.split(/[,;]\s*/).map(p => p.trim()).filter(p => p.length > 0);
    if (parts.length > 1) return parts;
    return [opts];
  }
  return [];
};

// 将保存的数据（可能是字母、数字、选项文本或对象）标准化为组件需要的结构
const normalizeSavedUserAnswers = (uaRaw, questionList) => {
  const out = {};
  if (!uaRaw) return out;
  try {
    Object.keys(uaRaw).forEach(k => {
      const v = uaRaw[k];
      let qi = parseInt(k, 10);
      if (isNaN(qi)) {
        const m = String(k).match(/(\d+)$/);
        qi = m ? parseInt(m[1], 10) : NaN;
      }
      // 如果 key 可能是 1-based（历史格式），对齐到 0-based
      if (!isNaN(qi) && questionList && questionList.length > 0) {
        if (qi > 0 && qi > questionList.length - 1) {
          qi = qi - 1;
        }
      }
      const q = (questionList && !isNaN(qi) && questionList[qi]) || {};
      const opts = normalizeOptions(q) || [];

      if (v == null) return;
      // 如果已经是目标结构
      if (typeof v === 'object' && (v.selectedOptions || v.text)) {
        if (Array.isArray(v.selectedOptions)) {
          const indices = v.selectedOptions.map(val => {
            if (typeof val === 'number') return val;
            if (typeof val === 'string' && /^[A-Za-z]$/.test(val)) return val.toUpperCase().charCodeAt(0) - 65;
            if (typeof val === 'string' && /^\d+$/.test(val)) return parseInt(val, 10);
            return null;
          }).filter(x => x !== null);
          if (indices.length) out[qi] = { selectedOptions: indices, submitted: true }; else if (v.text) out[qi] = { text: v.text, submitted: true };
        } else if (v.text) {
          out[qi] = { text: v.text, submitted: true };
        } else {
          out[qi] = v;
        }
        return;
      }

      // 数组 -> 视为选项数组或索引数组
      if (Array.isArray(v)) {
        const indices = v.map(val => {
          if (typeof val === 'number') return val;
          if (typeof val === 'string' && /^[A-Za-z]$/.test(val)) return val.toUpperCase().charCodeAt(0) - 65;
          if (typeof val === 'string' && /^\d+$/.test(val)) return parseInt(val, 10);
          // 试图按选项文本匹配
          const fi = opts.findIndex(o => o && o.trim() === String(val).trim());
          return fi !== -1 ? fi : null;

        }).filter(x => x !== null);
        if (indices.length) { out[qi] = { selectedOptions: indices, submitted: true }; return; }
      }

      // 字符串：可能是 "A,B"、"A. 文本"、选项文本或开放题文本
      if (typeof v === 'string') {
        const s = v.trim();
        if (s.length === 0) return;
        // 逗号或中文逗号分隔的多个答案
        if (s.includes(',') || s.includes('，')) {
          const parts = s.split(/[,，]/).map(p => p.trim()).filter(Boolean);
          const indices = parts.map(p => {
            if (/^[A-Za-z]$/.test(p)) return p.toUpperCase().charCodeAt(0) - 65;
            if (/^\d+$/.test(p)) return parseInt(p, 10);
            const fi = opts.findIndex(o => o && o.trim() === p);
            if (fi !== -1) return fi;
            const fi2 = opts.findIndex(o => o && o.trim().startsWith(p));
            return fi2 !== -1 ? fi2 : null;
          }).filter(x => x !== null);
          if (indices.length) { out[qi] = { selectedOptions: indices, submitted: true }; return; }
        }

        // 单个字母或以字母开头
        if (/^[A-Za-z]/.test(s)) {
          const idx = s[0].toUpperCase().charCodeAt(0) - 65;
          if (!isNaN(idx) && idx >= 0 && idx < opts.length) { out[qi] = { selectedOptions: [idx], submitted: true }; return; }
        }

        // 尝试按文本精确或前缀匹配选项
        const foundExact = opts.findIndex(o => o && o.trim() === s);
        if (foundExact !== -1) { out[qi] = { selectedOptions: [foundExact], submitted: true }; return; }
        const foundPrefix = opts.findIndex(o => o && o.trim().startsWith(s));
        if (foundPrefix !== -1) { out[qi] = { selectedOptions: [foundPrefix], submitted: true }; return; }

        // 回退为文本（开放题场景）
        out[qi] = { text: s, submitted: true };
        return;
      }

      // 其它类型，转为文本保存
      out[qi] = { text: String(v), submitted: true };
    });
  } catch (e) {
    console.warn('normalizeSavedUserAnswers error', e);
  }
  return out;
};
const Question = ({ questionData, num, style, userAnswers, setUserAnswers, course, topic, inWrong, onToggleWrong }) => {
  // 统一规范题型，只允许七种
  const normalizeType = (t) => {
    const s = (t || '').toString().toLowerCase().trim();
    if (['single_choice', 'single-choice', 'single choice', 'single'].includes(s)) return 'single_choice';
    if (['multiple_choice', 'multiple-choice', 'multiple choice', 'multi_choice', 'multi'].includes(s)) return 'multiple_choice';
    if (['short_answer', 'short-answer', 'short answer'].includes(s)) return 'short_answer';
    if (['calculation', 'calc', 'compute'].includes(s)) return 'calculation';
    if (['case_study', 'case-study', 'case study'].includes(s)) return 'case_study';
    if (['true_false', 'true-false', 'truefalse', 'tf', 'boolean'].includes(s)) return 'true_false';
    if (['fill_in_the_blank', 'fill-in-the-blank', 'fill in the blank', 'fill_blank'].includes(s)) return 'fill_in_the_blank';
    return s || 'short_answer';
  };

  const normalizedType = normalizeType(questionData.type);
  // 仅这三类使用选项渲染，其余均视为开放题
  const isChoiceQuestion = ['single_choice', 'multiple_choice', 'true_false'].includes(normalizedType);
  // 是否为多选：由 correctAnswer 数组或明确的 multiple 标记决定
  const isMulti = normalizedType === 'multiple_choice' || Array.isArray(questionData.correctAnswer) || questionData.multiple === true;
  const [personalizedExplanation, setPersonalizedExplanation] = useState(null);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [explanationError, setExplanationError] = useState(null);
  const explanationLock = useRef(false);
  const [followUpQuestion, setFollowUpQuestion] = useState("");
  const [conversationHistory, setConversationHistory] = useState([]);
  const [loadingFollowUp, setLoadingFollowUp] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [questionScore, setQuestionScore] = useState(null);
  const [loadingScore, setLoadingScore] = useState(false);
  const [scoreError, setScoreError] = useState(null);

  const handleAnswerChange = (e) => {
    setUserAnswers(prev => ({
      ...prev,
      [num - 1]: { ...(prev[num - 1] || {}), text: e.target.value }
    }));
  };

  const handleOptionSelect = (index) => {
    const uaEntryForCheck = userAnswers[num - 1] || userAnswers[String(num - 1)];
    if (uaEntryForCheck?.submitted) return;

    setUserAnswers(prev => {
      const current = prev[num - 1] || {};
      const currentAnswers = current.selectedOptions || [];
      const isSelected = currentAnswers.includes(index);

      // 判定是否为多选（优先依据 questionData.multiple 或 correctAnswer 为数组）
      const isMulti = Array.isArray(questionData.correctAnswer) || questionData.multiple === true;

      if (!isMulti) {
        // 单选：选择一个即替换
        return {
          ...prev,
          [num - 1]: { ...current, selectedOptions: [index] }
        };
      }

      // 多选：切换
      if (isSelected) {
        return {
          ...prev,
          [num - 1]: { ...current, selectedOptions: currentAnswers.filter(i => i !== index) }
        };
      } else {
        return {
          ...prev,
          [num - 1]: { ...current, selectedOptions: [...currentAnswers, index] }
        };
      }
    });
  };

  // 将可能为字符串的 options 标准化为数组；true_false 强制为 True/False
  const normalizeOptions = (q) => {
    if (!q) return [];
    if (normalizedType === 'true_false') return ['True', 'False'];
    const opts = q.options;
    if (!opts) return [];
    if (Array.isArray(opts)) return opts.map(o => typeof o === 'string' ? o : String(o));
    if (typeof opts === 'string') {
      const lines = opts.split(/\r?\n/).map(l => l.trim()).filter(l => l.length > 0);
      if (lines.length > 1) {
        return lines.map(l => l.replace(/^\s*([A-Za-z0-9).-]+)\s*/, '').trim());
      }
      const parts = opts.split(/[,;]\s*/).map(p => p.trim()).filter(p => p.length > 0);
      if (parts.length > 1) return parts;
      return [opts];
    }
    return [];
  };

  const fetchPersonalizedExplanation = async (userAnswer, correctAnswer) => {
    if (explanationLock.current) return;
    explanationLock.current = true;
    setLoadingExplanation(true);
    setExplanationError(null);
    try {
      axios.defaults.baseURL = API_BASE;
      const response = await axios.post("/api/personalized-explanation", {
        question: questionData.question,
        userAnswer: userAnswer,
        correctAnswer: correctAnswer,
        questionType: normalizedType,
        course: course,
        topic: topic,
        subtopic: questionData.subtopic
      });
      
      if (response.data.error) {
        setExplanationError("获取解析失败，请稍后重试");
      } else {
        setPersonalizedExplanation(response.data);
      }
    } catch (error) {
      console.error("获取个性化解析失败:", error);
      setExplanationError("网络错误，请检查后端服务是否运行");
    } finally {
      explanationLock.current = false;
      setLoadingExplanation(false);
    }
  };

  const fetchQuestionScore = async (userAnswer) => {
    setLoadingScore(true);
    setScoreError(null);
    try {
      axios.defaults.baseURL = API_BASE;
      const response = await axios.post("/api/evaluate-question", {
        question: questionData,
        user_answer: userAnswer
      });

      if (response.data.success && response.data.evaluation) {
        setQuestionScore(response.data.evaluation);
        // 将分数保存到userAnswers中
        setUserAnswers(prev => {
          const current = prev[num - 1] || {};
          return {
            ...prev,
            [num - 1]: { ...current, score: response.data.evaluation.score }
          };
        });
      } else {
        setScoreError("评分失败，请稍后重试");
      }
    } catch (error) {
      console.error("获取题目分数失败:", error);
      setScoreError("网络错误，请检查后端服务是否运行");
    } finally {
      setLoadingScore(false);
    }
  };

  const handleFollowUpSubmit = async (e) => {
    e.preventDefault();
    if (!followUpQuestion.trim() || loadingFollowUp) return;

    const userAnswer = isChoiceQuestion
      ? selectedOptions.map(i => String.fromCharCode(65 + i)).join(", ")
      : (userAnswers[num - 1]?.text || "");
    
    const correctAnswerRaw = questionData.correctAnswer ?? questionData.answerIndex ?? questionData.answer;
    const correctOption = typeof correctAnswerRaw === 'string' 
      ? correctAnswerRaw.charCodeAt(0) - 65 
      : correctAnswerRaw;
    const optsForQA = normalizeOptions(questionData);
    const correctAnswer = isChoiceQuestion && correctOption !== undefined
      ? (optsForQA[correctOption] ?? questionData.options?.[correctOption])
      : (questionData.modelAnswer ?? questionData.correctAnswer ?? ("参考答案为：" + correctAnswerRaw));

    setLoadingFollowUp(true);
    try {
      axios.defaults.baseURL = API_BASE;
      const response = await axios.post("/api/quiz-followup", {
        question: questionData.question,
        userAnswer: userAnswer,
        correctAnswer: correctAnswer,
        questionType: normalizedType,
        course: course,
        topic: topic,
        subtopic: questionData.subtopic,
        conversationHistory: conversationHistory,
        userQuestion: followUpQuestion
      });

      if (response.data.error) {
        alert("追问失败，请稍后重试");
      } else {
        setConversationHistory(prev => [...prev, { user: followUpQuestion, ai: response.data.answer }]);
        setFollowUpQuestion("");
      }
    } catch (error) {
      console.error("追问失败:", error);
      alert("网络错误，请检查后端服务是否运行");
    } finally {
      setLoadingFollowUp(false);
    }
  };

  const handleStopAsking = () => {
    setIsAsking(false);
    setConversationHistory([]);
    setFollowUpQuestion("");
  };

  const handleStartAsking = () => {
    setIsAsking(true);
  };

  const handleConfirm = () => {
    setUserAnswers(prev => {
      const current = prev[num - 1] || {};
      return {
        ...prev,
        [num - 1]: { ...current, submitted: true }
      };
    });

    const ua = userAnswers[num - 1] || userAnswers[String(num - 1)] || {};
    const userAnswer = isChoiceQuestion
      ? (ua.selectedOptions || []).map(i => String.fromCharCode(65 + i)).join(", ")
      : (ua.text || "");

    const correctAnswerRaw = questionData.correctAnswer ?? questionData.answerIndex ?? questionData.answer;
    const correctOption = typeof correctAnswerRaw === 'string' 
      ? correctAnswerRaw.charCodeAt(0) - 65 
      : correctAnswerRaw;
    const optsForConfirm = normalizeOptions(questionData);
    const correctAnswer = isChoiceQuestion && correctOption !== undefined
      ? (optsForConfirm[correctOption] ?? questionData.options?.[correctOption])
      : (questionData.modelAnswer ?? questionData.correctAnswer ?? ("参考答案为：" + correctAnswerRaw));

    fetchPersonalizedExplanation(userAnswer, correctAnswer);
    fetchQuestionScore(userAnswer);
  };

  const uaEntry = userAnswers[num - 1] || userAnswers[String(num - 1)] || {};
  console.log(`[quiz] Question ${num} uaEntry:`, uaEntry);
  const isSubmitted = (uaEntry && uaEntry.submitted) === true;
  const selectedOptions = (uaEntry && uaEntry.selectedOptions) || [];

  // 解析正确答案为索引数组的帮助函数
  const getCorrectIndices = (q) => {
    const raw = q.correctAnswer ?? q.answerIndex ?? q.answer;
    const opts = normalizeOptions(q) || [];
    const indices = [];
    if (raw === undefined || raw === null) return [];

    const pushParsed = (val) => {
      if (typeof val === 'number') {
        if (val >= 0 && val < opts.length) indices.push(val);
        return;
      }
      if (typeof val === 'string') {
        const s = val.trim();
        if (s.length === 0) return;
        // 如果以字母开头（如A 或 A. 文本）
        const m = s.match(/^[A-Za-z]/);
        if (m) {
          const letter = s[0].toUpperCase();
          if (letter >= 'A' && letter <= 'Z') {
            const idx = letter.charCodeAt(0) - 65;
            if (idx >= 0 && idx < opts.length) {
              indices.push(idx);
              return;
            }
          }
        }

        // 尝试按选项文本精确匹配（优先）
        const foundExact = opts.findIndex(o => o && o.trim() === s);
        if (foundExact !== -1) { indices.push(foundExact); return; }
        // 次优匹配：当长度>=4时允许前缀匹配以容错
        if (s.length >= 4) {
          const foundPrefix = opts.findIndex(o => o && o.trim().startsWith(s));
          if (foundPrefix !== -1) { indices.push(foundPrefix); return; }
          const foundContains = opts.findIndex(o => o && o.trim().includes(s));
          if (foundContains !== -1) { indices.push(foundContains); return; }
        }
      }
    };

    if (Array.isArray(raw)) {
      raw.forEach(r => pushParsed(r));
    } else {
      pushParsed(raw);
    }

    // 去重
    return Array.from(new Set(indices));
  };

  if (isChoiceQuestion) {
    const optionsArray = normalizeOptions(questionData);
    const correctIndices = getCorrectIndices(questionData);

    return (
      <div className="question" style={style}>
        <div className="question-head">
          <h3>
            <span style={{ marginRight: "1ch" }}>{num + "."}</span>
            <span style={{ marginRight: "0.8ch", color: '#9aa' }}>
              {(questionData.multiple || correctIndices.length > 1) ? '多选' : '单选'}
            </span>
            {questionData.question}
          </h3>
          {onToggleWrong && (
            <button className={`wrong-toggle ${inWrong ? 'active' : ''}`} onClick={onToggleWrong}>
              {inWrong ? '已在错题集' : '加入错题'}
            </button>
          )}
        </div>
        <div className="flexbox options">
          {optionsArray.map((option, index) => {
            const isSelected = selectedOptions.includes(index);
            const isCorrect = correctIndices.includes(index);
            const isUserWrong = isSubmitted && isSelected && !isCorrect;
            const isUserCorrect = isSubmitted && isSelected && isCorrect;
            const isMissed = isSubmitted && !isSelected && isCorrect;

            let cls = '';
            if (isUserCorrect) cls = 'correct';
            else if (isUserWrong) cls = 'wrong';
            else if (isMissed) cls = isMulti ? 'missed' : 'correct';

            return (
              <div 
                className={`option ${cls} ${isSelected ? 'selected' : ''} ${isSubmitted ? 'attempted' : ''}`}
                key={index}
                onClick={() => handleOptionSelect(index)}
              >
                <span className="option-marker">{String.fromCharCode(65 + index)}.</span>
                <span className="option-text">{option}</span>
                {isSubmitted && (
                  <>
                    {isUserCorrect && (
                      <CircleCheck className="optionIcon" size={35} strokeWidth={1} color="#00FFE0" />
                    )}
                    {isUserWrong && (
                      <CircleX className="optionIcon" size={35} strokeWidth={1} color="#FF3D00" />
                    )}
                    {isMissed && isMulti && (
                      <CircleCheck className="optionIcon" size={35} strokeWidth={1} color="#FFD166" />
                    )}
                    {isMissed && !isMulti && (
                      <CircleCheck className="optionIcon" size={35} strokeWidth={1} color="#00FFE0" />
                    )}
                  </>
                )}
              </div>
            );
          })}
          {!isSubmitted && selectedOptions.length > 0 && (
            <button className="confirm-button" onClick={handleConfirm}>
              确认答案
            </button>
          )}
            {isSubmitted && (
            <div className="answer-result">
              {loadingScore && (
                <div className="loading-score">
                  <span className="loading-spinner"></span>
                  正在评分...
                </div>
              )}
              {scoreError && (
                <div className="score-error">
                  <CircleX size={20} strokeWidth={2} color="#FF3D00" />
                  <span>{scoreError}</span>
                </div>
              )}
              {questionScore && !loadingScore && (
                <div className="question-score">
                  <div className={`score-badge ${questionScore.score === 10 ? 'perfect' : questionScore.score >= 7 ? 'good' : 'needs-improvement'}`}>
                    <span className="score-number">{questionScore.score}</span>
                    <span className="score-label">分</span>
                  </div>
                  {questionScore.feedback && (
                    <div className="score-feedback">
                      <strong>评价：</strong>{questionScore.feedback}
                    </div>
                  )}
                  {questionScore.strengths && questionScore.strengths.length > 0 && (
                    <div className="score-strengths">
                      <strong>优点：</strong>
                      <ul>
                        {questionScore.strengths.map((strength, idx) => (
                          <li key={idx}>{strength}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {questionScore.improvements && questionScore.improvements.length > 0 && (
                    <div className="score-improvements">
                      <strong>改进建议：</strong>
                      <ul>
                        {questionScore.improvements.map((improvement, idx) => (
                          <li key={idx}>{improvement}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
              {correctIndices && correctIndices.length > 0 ? (
                <div className="correct-answer">
                  <CircleCheck size={24} strokeWidth={2} color="#00FFE0" />
                  <span>正确答案：{correctIndices.map((ci, idx) => (
                    <span key={ci} style={{marginRight: '0.6ch'}}>{String.fromCharCode(65 + ci)}. {optionsArray[ci] ?? questionData.options?.[ci] ?? ''}</span>
                  ))}</span>
                </div>
              ) : (
                <div className="correct-answer">
                  <CircleCheck size={24} strokeWidth={2} color="#00FFE0" />
                  <span>正确答案：{questionData.correctAnswer ?? '（参考答案未提供）'}</span>
                </div>
              )}
              {(questionData.explanation || questionData.reason) && (
                <div className="reason">
                  <strong>解析：</strong>{questionData.explanation ?? questionData.reason}
                </div>
              )}
              {loadingExplanation && (
                <div className="loading-explanation">
                  <span className="loading-spinner"></span>
                  正在生成个性化解析...
                </div>
              )}
              {explanationError && (
                <div className="explanation-error">
                  <CircleX size={20} strokeWidth={2} color="#FF3D00" />
                  <span>{explanationError}</span>
                </div>
              )}
              {personalizedExplanation && (
                <div className="personalized-explanation">
                  <div className="explanation-section analysis">
                    <strong>📊 分析：</strong>
                    {personalizedExplanation.analysis}
                  </div>
                  {personalizedExplanation.correction && (
                    <div className="explanation-section correction">
                      <strong>纠正：</strong>
                      {personalizedExplanation.correction}
                    </div>
                  )}
                  {personalizedExplanation.suggestion && (
                    <div className="explanation-section suggestion">
                      <strong>💡 建议：</strong>
                      {personalizedExplanation.suggestion}
                    </div>
                  )}
                  {personalizedExplanation.encouragement && (
                    <div className="explanation-section encouragement">
                      <strong>🌟 鼓励：</strong>
                      {personalizedExplanation.encouragement}
                    </div>
                  )}
                </div>
              )}
              {isSubmitted && personalizedExplanation && (
                <div className="followup-section">
                  {!isAsking ? (
                    <button className="ask-button" onClick={handleStartAsking}>
                      💬 有疑问？继续追问
                    </button>
                  ) : (
                    <div className="followup-container">
                      <div className="followup-header">
                        <strong>💬 追问题目</strong>
                        <button className="stop-button" onClick={handleStopAsking}>
                          停止追问
                        </button>
                      </div>
                      
                      {conversationHistory.length > 0 && (
                        <div className="conversation-history">
                          {conversationHistory.map((chat, index) => (
                            <div key={index} className="conversation-item">
                              <div className="user-question">
                                <span className="question-label">你：</span>
                                <span>{chat.user}</span>
                              </div>
                              <div className="ai-answer">
                                <span className="answer-label">AI：</span>
                                <span>{chat.ai}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                      
                      <form className="followup-form" onSubmit={handleFollowUpSubmit}>
                        <input
                          type="text"
                          className="followup-input"
                          placeholder="输入你的问题..."
                          value={followUpQuestion}
                          onChange={(e) => setFollowUpQuestion(e.target.value)}
                          disabled={loadingFollowUp}
                        />
                        <button 
                          type="submit" 
                          className="submit-followup-button"
                          disabled={!followUpQuestion.trim() || loadingFollowUp}
                        >
                          {loadingFollowUp ? "发送中..." : "发送"}
                        </button>
                      </form>
                    </div>
                  )}
                </div>
              )}
              {/* 在查看模式下允许手动生成个性化解析 */}
              {!isSubmitted && !isAsking && (
                <></>
              )}
              {isSubmitted && !personalizedExplanation && !loadingExplanation && (
                <div style={{ marginTop: '0.6rem' }}>
                  <button className="ask-button" onClick={() => fetchPersonalizedExplanation(isChoiceQuestion ? (selectedOptions || []).map(i=>String.fromCharCode(65+i)).join(', ') : (userAnswers[num-1]?.text || ''), (correctIndices && correctIndices.length>0 ? (correctIndices.map(i=> questionData.options[i]).join(', ') ) : (questionData.modelAnswer || questionData.correctAnswer)))}>
                    生成个性化解析
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="question" style={style}>
      <div className="question-head">
        <h3>
          <span style={{ marginRight: "1ch" }}>{num + "."}</span>
          <span style={{ marginRight: "0.8ch", color: '#9aa' }}>
            {(() => {
              switch (normalizedType) {
                case 'single_choice': return '单选';
                case 'multiple_choice': return '多选';
                case 'short_answer': return '简答';
                case 'calculation': return '计算';
                case 'case_study': return '案例分析';
                case 'true_false': return '判断';
                case 'fill_in_the_blank': return '填空';
                default:
                  return '';
              }
            })()}
          </span>
          {questionData.question}
        </h3>
        {onToggleWrong && (
          <button className={`wrong-toggle ${inWrong ? 'active' : ''}`} onClick={onToggleWrong}>
            {inWrong ? '已在错题集' : '加入错题'}
          </button>
        )}
      </div>
      <div className="options">
        <textarea
          className="answer-input"
          placeholder="请在此输入你的答案..."
          value={userAnswers[num - 1]?.text || ""}
          onChange={handleAnswerChange}
          disabled={isSubmitted}
        />
        {!isSubmitted && (userAnswers[num - 1] && userAnswers[num - 1].text && userAnswers[num - 1].text.trim() !== "") && (
          <button className="confirm-button" onClick={handleConfirm}>
            确认答案
          </button>
        )}
        {isSubmitted && (
          <div className="result-section">
            {loadingScore && (
              <div className="loading-score">
                <span className="loading-spinner"></span>
                正在评分...
              </div>
            )}
            {scoreError && (
              <div className="score-error">
                <CircleX size={20} strokeWidth={2} color="#FF3D00" />
                <span>{scoreError}</span>
              </div>
            )}
            {questionScore && !loadingScore && (
              <div className="question-score">
                <div className={`score-badge ${questionScore.score === 10 ? 'perfect' : questionScore.score >= 7 ? 'good' : 'needs-improvement'}`}>
                  <span className="score-number">{questionScore.score}</span>
                  <span className="score-label">分</span>
                </div>
                {questionScore.feedback && (
                  <div className="score-feedback">
                    <strong>评价：</strong>{questionScore.feedback}
                  </div>
                )}
                {questionScore.strengths && questionScore.strengths.length > 0 && (
                  <div className="score-strengths">
                    <strong>优点：</strong>
                    <ul>
                      {questionScore.strengths.map((strength, idx) => (
                        <li key={idx}>{strength}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {questionScore.improvements && questionScore.improvements.length > 0 && (
                  <div className="score-improvements">
                    <strong>改进建议：</strong>
                    <ul>
                      {questionScore.improvements.map((improvement, idx) => (
                        <li key={idx}>{improvement}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
            {(questionData.modelAnswer || questionData.correctAnswer || questionData.answer || questionData.answerText) && (
              <div className="model-answer">
                <div className="model-answer-header">
                  <CircleCheck size={24} strokeWidth={2} color="#00FFE0" />
                  <strong>参考答案：</strong>
                </div>
                <div className="model-answer-content">
                  {questionData.modelAnswer || questionData.correctAnswer || questionData.answer || questionData.answerText}
                </div>
              </div>
            )}
            {questionData.keyPoints && (
              <div className="key-points">
                <strong>要点提示：</strong>
                <ul>
                  {Array.isArray(questionData.keyPoints) 
                    ? questionData.keyPoints.map((point, i) => <li key={i}>{point}</li>)
                    : <li>{questionData.keyPoints}</li>
                  }
                </ul>
              </div>
            )}
            {(questionData.explanation || questionData.reason) && (
              <div className="reason">
                <strong>解析：</strong>
                {questionData.explanation ?? questionData.reason}
              </div>
            )}
            {isSubmitted && !personalizedExplanation && !loadingExplanation && (
              <div style={{ marginTop: '0.6rem' }}>
                <button className="ask-button" onClick={() => fetchPersonalizedExplanation(uaEntry?.text || '', (questionData.modelAnswer || questionData.correctAnswer))}>
                  生成个性化解析
                </button>
              </div>
            )}
            {loadingExplanation && (
              <div className="loading-explanation">
                <span className="loading-spinner"></span>
                正在生成个性化解析...
              </div>
            )}
            {explanationError && (
              <div className="explanation-error">
                <CircleX size={20} strokeWidth={2} color="#FF3D00" />
                <span>{explanationError}</span>
              </div>
            )}
            {personalizedExplanation && (
              <div className="personalized-explanation">
                <div className="explanation-section analysis">
                  <strong>📊 分析：</strong>
                  {personalizedExplanation.analysis}
                </div>
                {personalizedExplanation.correction && (
                  <div className="explanation-section correction">
                    <strong>纠正：</strong>
                    {personalizedExplanation.correction}
                  </div>
                )}
                {personalizedExplanation.suggestion && (
                  <div className="explanation-section suggestion">
                    <strong>💡 建议：</strong>
                    {personalizedExplanation.suggestion}
                  </div>
                )}
                {personalizedExplanation.encouragement && (
                  <div className="explanation-section encouragement">
                    <strong>🌟 鼓励：</strong>
                    {personalizedExplanation.encouragement}
                  </div>
                )}
              </div>
            )}
            {isSubmitted && personalizedExplanation && (
              <div className="followup-section">
                {!isAsking ? (
                  <button className="ask-button" onClick={handleStartAsking}>
                    💬 有疑问？继续追问
                  </button>
                ) : (
                  <div className="followup-container">
                    <div className="followup-header">
                      <strong>💬 追问题目</strong>
                      <button className="stop-button" onClick={handleStopAsking}>
                        停止追问
                      </button>
                    </div>
                    
                    {conversationHistory.length > 0 && (
                      <div className="conversation-history">
                        {conversationHistory.map((chat, index) => (
                          <div key={index} className="conversation-item">
                            <div className="user-question">
                              <span className="question-label">你：</span>
                              <span>{chat.user}</span>
                            </div>
                            <div className="ai-answer">
                              <span className="answer-label">AI：</span>
                              <span>{chat.ai}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    <form className="followup-form" onSubmit={handleFollowUpSubmit}>
                      <input
                        type="text"
                        className="followup-input"
                        placeholder="输入你的问题..."
                        value={followUpQuestion}
                        onChange={(e) => setFollowUpQuestion(e.target.value)}
                        disabled={loadingFollowUp}
                      />
                      <button 
                        type="submit" 
                        className="submit-followup-button"
                        disabled={!followUpQuestion.trim() || loadingFollowUp}
                      >
                        {loadingFollowUp ? "发送中..." : "发送"}
                      </button>
                    </form>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

const QuizPage = (props) => {
  const [searchParams] = useSearchParams();
  const [subtopic, setSubtopic] = useState("");
  const [description, setDescription] = useState("");
  const [topic, setTopic] = useState("");
  const [questions, setQuestions] = useState([]);
  const [userAnswers, setUserAnswers] = useState({});
  const [wrongFlags, setWrongFlags] = useState({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [viewMode, setViewMode] = useState(false);
  const [startTime] = useState(() => new Date().getTime());
  const [numQues, setNumQues] = useState(0);

  const navigate = useNavigate();

  const course = searchParams.get("topic");
  const weekNum = searchParams.get("week");
  const subtopicNum = searchParams.get("subtopic");
  if (!course || !weekNum || !subtopicNum) {
    navigate("/");
  }
  useEffect(() => {
    let topics = JSON.parse(localStorage.getItem("topics")) || {};
    const roadmaps = JSON.parse(localStorage.getItem("roadmaps")) || {};

    if (
      !Object.keys(roadmaps).includes(course) ||
      !Object.keys(topics).includes(course)
    ) {
      navigate("/");
    }
    const week = Object.keys(roadmaps[course])[weekNum - 1];
    setTopic(roadmaps[course][week].topic);
    console.log(weekNum, week, Object.keys(roadmaps[course]));
    setSubtopic(roadmaps[course][week].subtopics[subtopicNum - 1].subtopic);
    setDescription(
      roadmaps[course][week].subtopics[subtopicNum - 1].description
    );
  }, [course, weekNum, subtopicNum, navigate]);

  useEffect(() => {
    const load = async () => {
      // 进入加载流程时先显示 loading，直到题目就绪
      setLoading(true);
      console.log('[quiz] loader start', { course, weekNum, subtopicNum, topic, subtopic, description });
      const view = searchParams.get('view') === 'true';
      setViewMode(view);

      // 非查看模式：生成/重新测验前先清理后端旧记录，避免重复
      if (!view && course && weekNum && subtopicNum) {
        try {
          axios.defaults.baseURL = 'http://localhost:5000';
          console.log('[quiz] pre-clean delete-quiz-records', { course, weekNum, subtopicNum });
          const delRes = await axios.post('/api/delete-quiz-records', {
            course,
            week: weekNum,
            subtopic: subtopicNum
          });
          console.log('[quiz] pre-clean delete-quiz-records done', delRes && delRes.data);
        } catch (err) {
          console.warn('预清理后端旧测验记录失败（继续尝试生成新题）', err);
        }
      }

      const quizzes = JSON.parse(localStorage.getItem("quizzes")) || {};

      // 使用 normalizeSavedUserAnswers 来将保存的答案标准化为组件可用结构

      if (view) {
        if (!course || !weekNum || !subtopicNum) {
          console.log('[quiz] loader: missing identifiers for view-mode', { course, weekNum, subtopicNum });
          return;
        }

        console.log('[quiz] view-mode: checking local savedQuizzes', { course, weekNum, subtopicNum });
        const saved = JSON.parse(localStorage.getItem('savedQuizzes')) || {};
        if (saved[course] && saved[course][weekNum] && saved[course][weekNum][subtopicNum]) {
          console.log('[quiz] view-mode: found local savedQuizzes entry');
          const entry = saved[course][weekNum][subtopicNum];
          // 支持历史/后端记录嵌套在 record 下的情况
          const questionList = (entry.questions && entry.questions.length > 0)
            ? entry.questions
            : (entry.record && entry.record.questions ? entry.record.questions : []);
          const uaRaw = (entry.userAnswers && Object.keys(entry.userAnswers).length > 0)
            ? entry.userAnswers
            : (entry.record && entry.record.userAnswers ? entry.record.userAnswers : {});
            const ua = normalizeSavedUserAnswers(uaRaw || {}, questionList);
            console.log('[quiz] view-mode: local entry loaded', { entry, uaRaw, ua });
            setQuestions(questionList || []);
            setNumQues((questionList || []).length);
            setUserAnswers(ua);
          setLoading(false);
          return;
        }

        // 尝试从后端获取
        try {
          axios.defaults.baseURL = 'http://localhost:5000';
          console.log('[quiz] view-mode: requesting /api/quiz-records', { course, week: weekNum, subtopic: subtopicNum });
          const res = await axios.get('/api/quiz-records', {
            params: { course, week: weekNum, subtopic: subtopicNum }
          });
          console.log('[quiz] view-mode: /api/quiz-records response', res && res.data ? res.data : res);
          if (res.data && res.data.success && res.data.records && res.data.records.length > 0) {
            const rec = res.data.records[0];
            const entry = rec.record || {};
            const questionList = (entry.questions && entry.questions.length > 0)
              ? entry.questions
              : (entry.record && entry.record.questions ? entry.record.questions : []);
            const uaRaw = (entry.userAnswers && Object.keys(entry.userAnswers).length > 0)
              ? entry.userAnswers
              : (entry.record && entry.record.userAnswers ? entry.record.userAnswers : {});
              const ua = normalizeSavedUserAnswers(uaRaw || {}, questionList);
              console.log('[quiz] view-mode: backend entry loaded', { rec, entry, uaRaw, ua });
              setQuestions(questionList || []);
              setNumQues((questionList || []).length);
              setUserAnswers(ua);
            setLoading(false);
            return;
          }
        } catch (err) {
          console.warn('从后端获取测验记录失败，回退到本地或重新生成', err);
        }
      }

      // 非 view 或未找到记录时生成/读取缓存
      if (
        quizzes[course] &&
        quizzes[course][weekNum] &&
        quizzes[course][weekNum][subtopicNum]
      ) {
        setQuestions(quizzes[course][weekNum][subtopicNum]);
        setNumQues(quizzes[course][weekNum][subtopicNum].length);
        setLoading(false);
        return;
      }

      try {
        console.log("fetching questions...");
        axios.defaults.baseURL = API_BASE;
        const res = await axios.post('/api/quiz', { course, topic, subtopic, description });
        setQuestions(res.data.questions);
        setNumQues(res.data.questions.length);
        quizzes[course] = quizzes[course] || {};
        quizzes[course][weekNum] = quizzes[course][weekNum] || {};
        quizzes[course][weekNum][subtopicNum] = res.data.questions;
        localStorage.setItem("quizzes", JSON.stringify(quizzes));

        // 生成题目后保存初始记录（题目/正确答案/解析，用户答案为空）
        try {
          axios.defaults.baseURL = API_BASE;
          const initialRecord = {
            numQues: res.data.questions.length,
            numCorrect: 0,
            scorable: res.data.questions.filter(q => q.options && q.options.length > 0).length,
            scorePercent: null,
            timeTaken: 0,
            userAnswers: {},
            questions: res.data.questions,
            completedAt: null
          };
          console.log('[quiz] save initial record', { course, weekNum, subtopicNum, numQues: initialRecord.numQues });
          const saveInitRes = await axios.post('/api/save-quiz-record', {
            course,
            week: weekNum,
            subtopic: subtopicNum,
            record: initialRecord
          });
          console.log('[quiz] save initial record done', saveInitRes && saveInitRes.data);
        } catch (err) {
          console.warn('生成题目后保存初始测验记录失败（不影响继续答题）', err);
        }
        setLoading(false);
      } catch (error) {
        console.log(error);
        if (!window.__quiz_error_shown) {
          alert("An error occured while fetching the quiz. Please try again later.");
          window.__quiz_error_shown = true;
        }
        setLoading(false);
      }
    };

    load();
  }, [course, topic, subtopic, description, weekNum, subtopicNum, searchParams]);

  // 自动保存草稿（用户在答题过程中退出，可继续作答）
  useEffect(() => {
    if (!course || !weekNum || !subtopicNum) return;
    const draftKey = 'savedQuizzes';
    try {
      const saved = JSON.parse(localStorage.getItem(draftKey)) || {};
      saved[course] = saved[course] || {};
      saved[course][weekNum] = saved[course][weekNum] || {};
      const existing = saved[course][weekNum][subtopicNum] || {};
      saved[course][weekNum][subtopicNum] = {
        questions: questions,
        userAnswers: userAnswers,
        record: existing.record || null
      };
      localStorage.setItem(draftKey, JSON.stringify(saved));
    } catch (e) {
      console.warn('自动保存测验草稿失败', e);
    }
  }, [userAnswers, questions, course, weekNum, subtopicNum]);

  // 查询当前题目哪些已在错题集
  useEffect(() => {
    if (!course || !weekNum || !subtopicNum) return;
    if (!questions || questions.length === 0) return;
    const run = async () => {
      try {
        axios.defaults.baseURL = 'http://localhost:5000';
        const res = await axios.post('/api/wrong-questions/check', {
          course,
          week: weekNum,
          subtopic: subtopicNum,
          questions,
        });
        if (res.data && res.data.success) {
          const map = {};
          (res.data.indices || []).forEach(i => { map[i] = true; });
          setWrongFlags(map);
        }
      } catch (e) {
        console.warn('查询错题 membership 失败', e);
      } finally {
      }
    };
    run();
  }, [course, weekNum, subtopicNum, questions]);

  const formatCorrectToken = (token, opts) => {
    if (token === undefined || token === null) return '';
    if (typeof token === 'number' && opts && opts[token]) return opts[token];
    if (typeof token === 'string') {
      const trimmed = token.trim();
      if (/^[A-Za-z]$/.test(trimmed)) {
        const idx = trimmed.toUpperCase().charCodeAt(0) - 65;
        if (opts && opts[idx]) return opts[idx];
      }
      return trimmed;
    }
    return String(token);
  };

  const computeCorrectText = (q) => {
    const opts = normalizeOptions(q);
    const raw = q.correctAnswer ?? q.answerIndex ?? q.answer;
    if (Array.isArray(raw)) {
      const parts = raw.map(r => formatCorrectToken(r, opts)).filter(Boolean);
      if (parts.length) return parts.join(', ');
    }
    const single = formatCorrectToken(raw, opts) || q.modelAnswer || q.correctAnswer || '';
    return single;
  };

  const computeUserAnswerText = (idx) => {
    const q = questions[idx];
    if (!q) return '';
    const ua = userAnswers[idx] || userAnswers[String(idx)] || {};
    const opts = normalizeOptions(q);
    if (ua.selectedOptions && ua.selectedOptions.length > 0) {
      return ua.selectedOptions.map(i => opts[i] || String.fromCharCode(65 + (i || 0))).join(', ');
    }
    if (ua.text) return ua.text;
    return '';
  };

  const handleToggleWrong = async (index) => {
    const q = questions[index];
    if (!q) return;
    try {
      axios.defaults.baseURL = 'http://localhost:5000';
      const payload = {
        course,
        week: weekNum,
        subtopic: subtopicNum,
        question: q,
        user_answer: computeUserAnswerText(index),
        correct_answer: computeCorrectText(q),
        difficulty: q.difficulty,
      };
      const res = await axios.post('/api/wrong-questions/toggle', payload);
      if (res.data && res.data.success) {
        setWrongFlags(prev => ({ ...prev, [index]: res.data.inWrong }));
      }
    } catch (e) {
      console.warn('切换错题状态失败', e);
      alert('操作失败，请稍后重试');
    }
  };

  const SubmitButton = () => {
    // 加载中或暂无题目时不渲染提交按钮，避免空白页只剩按钮
    if (loading || !questions || questions.length === 0) return null;

    return (
      <div className="submit">
        {!viewMode && (
          <button
            className="SubmitButton"
            disabled={submitting}
            onClick={async () => {
              setSubmitting(true);
              const timeTaken = new Date().getTime() - startTime;

              // 计算总分（每题0分，使用百分制）
              let totalScore = 0;
              let totalPossibleScore = 0;
              
              for (let i = 0; i < questions.length; i++) {
                const q = questions[i];
                const ua = userAnswers[i] || {};
                const qType = q.type ? q.type.toLowerCase() : '';
                
                // 每题满分10分
                totalPossibleScore += 10;
                
                // 选择题类型：single_choice, multiple_choice, true_false
                const isChoiceQuestion = ['single_choice', 'multiple_choice', 'true_false'].includes(qType);
                
                if (isChoiceQuestion && q.options && q.options.length > 0) {
                  // 选择题：全部选对得10分，否则0分
                  const parseCorrect = (raw, opts) => {
                    const indices = [];
                    if (raw === undefined || raw === null) return indices;
                    const push = (val) => {
                      if (typeof val === 'number') {
                        if (val >= 0 && val < opts.length) indices.push(val);
                        return;
                      }
                      if (typeof val === 'string') {
                        const s = val.trim();
                        if (s.length === 0) return;
                        const m = s.match(/^[A-Za-z]/);
                        if (m) {
                          const letter = s[0].toUpperCase();
                          if (letter >= 'A' && letter <= 'Z') {
                            const idx = letter.charCodeAt(0) - 65;
                            if (idx >= 0 && idx < opts.length) {
                              indices.push(idx);
                              return;
                            }
                          }
                        }
                        const found = opts.findIndex(o => o && (o.trim() === s || o.trim().startsWith(s) || s.startsWith(o.trim())));
                        if (found !== -1) indices.push(found);
                      }
                    };
                    if (Array.isArray(raw)) raw.forEach(r => push(r)); else push(raw);
                    return Array.from(new Set(indices));
                  };

                  const correctRaw = q.correctAnswer ?? q.answerIndex ?? q.answer;
                  const correctIndices = parseCorrect(correctRaw, normalizeOptions(q));
                  const selected = ua.selectedOptions || [];

                  if (correctIndices.length > 0) {
                    const selSet = new Set(selected || []);
                    const corrSet = new Set(correctIndices);
                    if (selSet.size === corrSet.size && [...selSet].every(x => corrSet.has(x))) {
                      totalScore += 10;
                    }
                  }
                } else {
                  // 非选择题：使用AI评估的分数（如果有）
                  if (ua.score !== undefined && ua.score !== null) {
                    totalScore += ua.score;
                  }
                }
              }

              // 计算百分制分数
              const scorePercent = totalPossibleScore > 0 ? Math.round((totalScore / totalPossibleScore) * 10000) / 100 : 0;

              const record = {
                numQues: numQues,
                totalScore: totalScore,
                totalPossibleScore: totalPossibleScore,
                scorePercent: scorePercent,
                timeTaken: timeTaken,
                userAnswers: userAnswers,
                questions: questions,
                completedAt: new Date().toISOString(),
              };

              try {
                // 先删除旧的测验记录
                try {
                  axios.defaults.baseURL = 'http://localhost:5000';
                  await axios.post('/api/delete-quiz-records', {
                    course,
                    week: weekNum,
                    subtopic: subtopicNum
                  });
                } catch (e) {
                  console.warn('后端测验记录删除失败', e);
                }

                // 再保存新测验记录（评分在后台完成）
                try {
                  axios.defaults.baseURL = API_BASE;
                  await axios.post('/api/save-quiz-record', {
                    course,
                    week: weekNum,
                    subtopic: subtopicNum,
                    record,
                  });
                } catch (err) {
                  console.warn('保存测验记录到后端失败，继续本地保存', err);
                }
              } finally {
                setSubmitting(false);
              }

              // 本地保存用于查看（即时响应）
              try {
                const saved = JSON.parse(localStorage.getItem('savedQuizzes')) || {};
                saved[course] = saved[course] || {};
                saved[course][weekNum] = saved[course][weekNum] || {};
                saved[course][weekNum][subtopicNum] = { questions, userAnswers, record };
                localStorage.setItem('savedQuizzes', JSON.stringify(saved));
              } catch (e) {
                console.warn('保存本地 savedQuizzes 失败', e);
              }

              // 更新 quizStats 本地展示（兼容原有路由页显示）
              try {
                const quizStats = JSON.parse(localStorage.getItem('quizStats')) || {};
                quizStats[course] = quizStats[course] || {};
                quizStats[course][weekNum] = quizStats[course][weekNum] || {};
                quizStats[course][weekNum][subtopicNum] = {
                  numQues: numQues,
                  timeTaken: timeTaken,
                  userAnswers: userAnswers,
                  completedAt: record.completedAt,
                  scorePercent: scorePercent,
                };
                localStorage.setItem('quizStats', JSON.stringify(quizStats));
              } catch (e) {
                console.warn('更新 quizStats 失败', e);
              }

              navigate(ROUTES.ROADMAP + '?topic=' + encodeURI(course));
            }}
          >
            {submitting ? '提交中...' : '提交'}
          </button>
        )}
      </div>
    );
  };

  if (loading || !questions || questions.length === 0) {
    return (
      <div className="quiz_wrapper">
        <Header></Header>
        <Loader style={{ display: "block" }}>
          正在为您生成个性化问题...
        </Loader>
      </div>
    );
  }

  return (
    <div className="quiz_wrapper">
      <Header></Header>
      <div className="content">
        <h1>{subtopic}</h1>
        <h3 style={{ opacity: "0.61", fontWeight: "300", marginBottom: "2em" }}>
          {description}
        </h3>
        {viewMode && !loading && questions.length === 0 && (
          <div style={{ border: '1px dashed #ccc', padding: '1rem', marginBottom: '1rem' }}>
            <strong>未找到测验记录</strong>
            <div style={{ marginTop: '0.5rem' }}>数据库记录可能已删除或本地缓存不存在。您可以重新答题或返回学习路径。</div>
            <div style={{ display: 'flex', gap: '0.6rem', marginTop: '0.8rem' }}>
              <button className="ask-button" onClick={() => {
                // 跳转到非查看模式重新答题
                navigate(ROUTES.QUIZ + `?topic=${encodeURIComponent(course)}&week=${weekNum}&subtopic=${subtopicNum}`);
              }}>重新答题</button>
              <button className="stop-button" onClick={() => {
                // 返回学习路径
                navigate(ROUTES.ROADMAP + `?topic=${encodeURI(course)}`);
              }}>返回学习路径</button>
            </div>
            <div style={{ marginTop: '1rem', fontSize: '0.9rem', opacity: 0.8 }}>
              如果需要，我也可以恢复本地缓存或重新生成题目。
            </div>
          </div>
        )}
        {/* 查看测验有数据时底部固定“重新测验”按钮 */}
        {questions.map((question, index) => {
          return (
            <Question 
              questionData={question} 
              num={index + 1} 
              userAnswers={userAnswers}
              setUserAnswers={setUserAnswers}
              course={course}
              topic={topic}
              inWrong={!!wrongFlags[index]}
              onToggleWrong={() => handleToggleWrong(index)}
            />
          );
        })}
          <SubmitButton />
          {/* 查看测验时，所有题目和提交按钮后显示“重新测验”按钮 */}
          {viewMode && !loading && questions.length > 0 && (
            <div style={{ margin: '2.5rem 0 1.5rem 0', display: 'flex', justifyContent: 'flex-end' }}>
              <button className="ask-button" onClick={async () => {
                setLoading(true);
                // 清空本地缓存
                const saved = JSON.parse(localStorage.getItem('savedQuizzes') || '{}');
                if (saved[course] && saved[course][weekNum] && saved[course][weekNum][subtopicNum]) {
                  delete saved[course][weekNum][subtopicNum];
                  localStorage.setItem('savedQuizzes', JSON.stringify(saved));
                }
                // 清空 quizzes 本地缓存（题目）
                const quizzes = JSON.parse(localStorage.getItem('quizzes') || '{}');
                if (quizzes[course] && quizzes[course][weekNum] && quizzes[course][weekNum][subtopicNum]) {
                  delete quizzes[course][weekNum][subtopicNum];
                  localStorage.setItem('quizzes', JSON.stringify(quizzes));
                }
                // 调用后端删除
                try {
                  axios.defaults.baseURL = 'http://localhost:5000';
                  await axios.post('/api/delete-quiz-records', {
                    course,
                    week: weekNum,
                    subtopic: subtopicNum
                  });
                } catch (e) {
                  console.warn('后端测验记录删除失败', e);
                }
                // 直接切换为作答模式并拉取新题
                setQuestions([]);
                setUserAnswers({});
                setNumQues(0);
                setViewMode(false);
                setTimeout(async () => {
                  try {
                    axios.defaults.baseURL = API_BASE;
                    const res = await axios.post('/api/quiz', { course, topic, subtopic, description });
                    setQuestions(res.data.questions);
                    setNumQues(res.data.questions.length);
                    // 更新 quizzes 本地缓存
                    const quizzesNew = JSON.parse(localStorage.getItem('quizzes') || '{}');
                    quizzesNew[course] = quizzesNew[course] || {};
                    quizzesNew[course][weekNum] = quizzesNew[course][weekNum] || {};
                    quizzesNew[course][weekNum][subtopicNum] = res.data.questions;
                    localStorage.setItem('quizzes', JSON.stringify(quizzesNew));

                    // 生成新题后立即保存初始测验记录到数据库
                    try {
                      axios.defaults.baseURL = API_BASE;
                      const initialRecord = {
                        numQues: res.data.questions.length,
                        numCorrect: 0,
                        scorable: res.data.questions.filter(q => q.options && q.options.length > 0).length,
                        scorePercent: null,
                        timeTaken: 0,
                        userAnswers: {},
                        questions: res.data.questions,
                        completedAt: null
                      };
                      await axios.post('/api/save-quiz-record', {
                        course,
                        week: weekNum,
                        subtopic: subtopicNum,
                        record: initialRecord
                      });
                    } catch (err) {
                      console.warn('生成新题后保存初始测验记录到后端失败', err);
                    }
                  } catch (error) {
                    alert("生成新测验失败，请稍后重试");
                  }
                  setLoading(false);
                }, 300);
              }}>重新测验</button>
            </div>
          )}
      </div>
    </div>
  );
};

export default QuizPage;
