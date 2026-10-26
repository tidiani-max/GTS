import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom"
import { PublicLayout } from "./components/PublicLayout"
import { About, Contact, Home, References, Services } from "./pages/PublicPages"
import { AdminApp, AdminLogin } from "./admin/AdminApp"
import { AuthProvider } from "./services/auth"

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<Home />} />
          <Route path="a-propos" element={<About />} />
          <Route path="references" element={<References />} />
          <Route path="services" element={<Services />} />
          <Route path="contact" element={<Contact />} />
        </Route>
        <Route path="/admin/login" element={<AdminLogin />} />
        <Route path="/admin/*" element={<AdminApp />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
