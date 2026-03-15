import { Toaster as SonnerToaster } from "sonner"
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import PageNotFound from '../lib/PageNotFound.jsx';

import AppLayout from './layout/AppLayout';
import Home from '../pages/Home';
import Upload from '../pages/Upload';
import Results from '../pages/Results';

function App() {
  return (
    <Router>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/Home" replace />} />
          <Route path="/Home" element={<Home />} />
          <Route path="/Upload" element={<Upload />} />
          <Route path="/Results" element={<Results />} />
        </Route>
        <Route path="*" element={<PageNotFound />} />
      </Routes>
      <SonnerToaster position="bottom-right" richColors />
    </Router>
  )
}

export default App