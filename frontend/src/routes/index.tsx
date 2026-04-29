import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "../components/layout/app-layout";
import { DashboardPage } from "../pages/DashboardPage";
import { DocumentDetailPage } from "../pages/DocumentDetailPage";
import { DocumentsPage } from "../pages/DocumentsPage";
import { EvaluationPage } from "../pages/EvaluationPage";
import { KnowledgeBaseDetailPage } from "../pages/KnowledgeBaseDetailPage";
import { KnowledgeBasesPage } from "../pages/KnowledgeBasesPage";
import { MinerUConfigPage } from "../pages/MinerUConfigPage";
import { RagPage } from "../pages/RagPage";
import { SettingsPage } from "../pages/SettingsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "knowledge-bases", element: <KnowledgeBasesPage /> },
      { path: "knowledge-bases/:kbId", element: <KnowledgeBaseDetailPage /> },
      { path: "documents", element: <DocumentsPage /> },
      { path: "documents/:documentId", element: <DocumentDetailPage /> },
      { path: "rag", element: <RagPage /> },
      { path: "mineru", element: <MinerUConfigPage /> },
      { path: "evaluation", element: <EvaluationPage /> },
      { path: "settings", element: <SettingsPage /> }
    ]
  }
]);

