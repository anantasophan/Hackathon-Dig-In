import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css';
import { configureAmplify } from './lib/amplify-config';
import CampaignComparisonPage from './pages/CampaignComparisonPage';
import CampaignOverviewPage from './pages/CampaignOverviewPage';
import CustomerCriteriaPage from './pages/CustomerCriteriaPage';
import RegionalPerformancePage from './pages/RegionalPerformancePage';
import TimeToTakeUpPage from './pages/TimeToTakeUpPage';
import SimilarCampaignPage from './pages/SimilarCampaignPage';

configureAmplify();

const PlaceholderPage: React.FC<{ title: string }> = ({ title }) => (
  <div style={{ padding: '2rem' }}><h1>{title}</h1><p>Implementation pending.</p></div>
);

const App: React.FC = () => (
  <Router>
    <Routes>
      <Route path="/" element={<Navigate to="/overview" replace />} />
      <Route path="/overview" element={<CampaignOverviewPage />} />
      <Route path="/comparison" element={<CampaignComparisonPage />} />
      <Route path="/time-analysis" element={<TimeToTakeUpPage />} />
      <Route path="/regional" element={<RegionalPerformancePage />} />
      <Route path="/customer-criteria" element={<CustomerCriteriaPage />} />
      <Route path="/similar-campaigns" element={<SimilarCampaignPage />} />
      <Route path="/login" element={<PlaceholderPage title="Login" />} />
    </Routes>
  </Router>
);

export default App;
