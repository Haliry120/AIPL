import React from "react";
import { RouterProvider, createBrowserRouter } from "react-router-dom";
import ReactDOM from "react-dom/client";
import "./index.css";
import { TopicPage, RoadmapPage, QuizPage, ProfilePage } from "./pages/index";
import { ROUTES } from './routes';
import App from "./App";
import reportWebVitals from "./reportWebVitals";

const router = createBrowserRouter([
  {
    path: ROUTES.HOME,
    element: <ProfilePage />,
  },
  {
    path: "/test",
    element: <App></App>,
  },
  {
    path: ROUTES.ROADMAP + '/',
    element: <RoadmapPage />,
  },
  {
    path: ROUTES.QUIZ + '/',
    element: <QuizPage />,
  },
  {
    path: ROUTES.TOPIC + '/',
    element: <TopicPage />,
  },
]);

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
