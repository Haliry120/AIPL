import React from "react";
import { RouterProvider, createBrowserRouter, Navigate } from "react-router-dom";
import ReactDOM from "react-dom/client";
import "./index.css";
import { TopicPage, RoadmapPage, QuizPage, ProfilePage, UserprofilePage, WrongPage, RedoPage, RedoPlayPage, LoginPage, RegisterPage, SettingsPage } from "./pages/index";
import { ROUTES } from './routes';
import App from "./App";
import reportWebVitals from "./reportWebVitals";
import userManager from "./utils/userManager";

const RequireAuth = ({ children }) => {
  if (!userManager.isAuthenticated()) {
    return <Navigate to={ROUTES.LOGIN} replace />;
  }
  return children;
};

const GuestOnly = ({ children }) => {
  if (userManager.isAuthenticated()) {
    return <Navigate to={ROUTES.HOME} replace />;
  }
  return children;
};

const router = createBrowserRouter([
  {
    path: ROUTES.HOME,
    element: (
      <RequireAuth>
        <ProfilePage />
      </RequireAuth>
    ),
  },
  {
    path: ROUTES.LOGIN,
    element: (
      <GuestOnly>
        <LoginPage />
      </GuestOnly>
    ),
  },
  {
    path: ROUTES.REGISTER,
    element: (
      <GuestOnly>
        <RegisterPage />
      </GuestOnly>
    ),
  },
  {
    path: ROUTES.PROFILE,
    element: (
      <RequireAuth>
        <UserprofilePage />
      </RequireAuth>
    ),
  },
  {
    path: ROUTES.SETTINGS,
    element: (
      <RequireAuth>
        <SettingsPage />
      </RequireAuth>
    ),
  },
  {
    path: "/test",
    element: <App></App>,
  },
  {
    path: ROUTES.ROADMAP + '/',
    element: (
      <RequireAuth>
        <RoadmapPage />
      </RequireAuth>
    ),
  },
  {
    path: ROUTES.QUIZ + '/',
    element: (
      <RequireAuth>
        <QuizPage />
      </RequireAuth>
    ),
  },
  {
    path: ROUTES.TOPIC + '/',
    element: (
      <RequireAuth>
        <TopicPage />
      </RequireAuth>
    ),
  },
  {
    path: ROUTES.WRONG + '/',
    element: (
      <RequireAuth>
        <WrongPage />
      </RequireAuth>
    ),
  },
  {
    path: ROUTES.REDO + '/',
    element: (
      <RequireAuth>
        <RedoPage />
      </RequireAuth>
    ),
  },
  {
    path: ROUTES.REDO_PLAY + '/',
    element: (
      <RequireAuth>
        <RedoPlayPage />
      </RequireAuth>
    ),
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
