import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Chat from './pages/Chat'
import DocumentDetail from './pages/DocumentDetail'
import Evaluation from './pages/Evaluation'
import Insights from './pages/Insights'
import Library from './pages/Library'
import Overview from './pages/Overview'
import Search from './pages/Search'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="documents" element={<Library />} />
          <Route path="documents/:id" element={<DocumentDetail />} />
          <Route path="chat" element={<Chat />} />
          <Route path="insights" element={<Insights />} />
          <Route path="search" element={<Search />} />
          <Route path="evaluation" element={<Evaluation />} />
          <Route path="settings" element={<Settings />} />
          <Route path="*" element={<p className="p-8">Page not found.</p>} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
