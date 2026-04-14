import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard/Dashboard';
import MethodologySearch from './pages/MethodologySearch/MethodologySearch';
import CreditAssessment from './pages/CreditAssessment/CreditAssessment';
import SurveillanceAlerts from './pages/SurveillanceAlerts/SurveillanceAlerts';
import PeerComparison from './pages/PeerComparison/PeerComparison';
import './App.css';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/search" element={<MethodologySearch />} />
        <Route path="/assessment" element={<CreditAssessment />} />
        <Route path="/surveillance" element={<SurveillanceAlerts />} />
        <Route path="/peer-comparison" element={<PeerComparison />} />
      </Route>
    </Routes>
  );
}
