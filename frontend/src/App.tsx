import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { configureAmplify } from './lib/amplify-config';
import AiRecommendationsPage from './pages/AiRecommendationsPage';
import CampaignComparisonPage from './pages/CampaignComparisonPage';
import CampaignOverviewPage from './pages/CampaignOverviewPage';
import CustomerCriteriaPage from './pages/CustomerCriteriaPage';
import RegionalPerformancePage from './pages/RegionalPerformancePage';
import TimeToTakeUpPage from './pages/TimeToTakeUpPage';
import SimilarCampaignPage from './pages/SimilarCampaignPage';

// Initialise Amplify (Cognito) before any component renders.
// Must be called at module scope so auth is ready on first render.
configureAmplify();

// Placeholder — pages implemented in tasks 11.x
const PlaceholderPage: React.FC<{ title: string }> = ({ title }) => (
  <div className="p-8">
    <h1>{title}</h1>
    <p>Implementation pending.</p>
  </div>
);

const App: React.FC = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<CampaignOverviewPage />} />
        <Route path="/comparison" element={<CampaignComparisonPage />} />
        <Route path="/time-analysis" element={<TimeToTakeUpPage />} />
        <Route path="/regional" element={<RegionalPerformancePage />} />
        <Route path="/customer-criteria" element={<CustomerCriteriaPage />} />
        <Route path="/similar-campaigns" element={<SimilarCampaignPage />} />
        <Route path="/ai-recommendations" element={<AiRecommendationsPage />} />
        <Route path="/login" element={<PlaceholderPage title="Login" />} />
      </Routes>
    </Router>
  );
};

export default App;
