import { BrowserRouter, Routes, Route } from 'react-router-dom';
import DashboardLayout from './layouts/DashboardLayout';
import PendingProposalsPage from './pages/PendingProposalsPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardLayout />}>
          <Route index element={<PendingProposalsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
