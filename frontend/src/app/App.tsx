import { Routes, Route, Navigate } from 'react-router-dom'
import DemoPage from '@/pages/DemoPage'

/**
 * App root.
 * Route yang tersedia sesuai spesifikasi Bagian 5:
 *   /demo  — satu-satunya halaman aktif MVP penyisihan
 *   /      — redirect ke /demo
 *   *      — redirect ke /demo (tidak ada 404 page)
 */
export default function App() {
  return (
    <Routes>
      <Route path="/demo" element={<DemoPage />} />
      <Route path="/" element={<Navigate to="/demo" replace />} />
      <Route path="*" element={<Navigate to="/demo" replace />} />
    </Routes>
  )
}
