import { Route, Routes } from "react-router-dom";
import { DashboardPage } from "../pages/DashboardPage";
import { RegisterCustomerPage } from "../pages/RegisterCustomerPage";
import { PledgeRecordsPage } from "../pages/PledgeRecordsPage";
import { PledgeDetailPage } from "../pages/PledgeDetailPage";
import { JewelleryIdentificationPage } from "../pages/JewelleryIdentificationPage";
import { MatchResultsPage } from "../pages/MatchResultsPage";
import { NotFoundPage } from "../pages/NotFoundPage";

export function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/register" element={<RegisterCustomerPage />} />
      <Route path="/pledges" element={<PledgeRecordsPage />} />
      <Route path="/pledges/:id" element={<PledgeDetailPage />} />
      <Route path="/identify" element={<JewelleryIdentificationPage />} />
      <Route path="/identify/results/:searchId" element={<MatchResultsPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
