import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppLayout } from '@/layouts/AppLayout'
import { AuthLayout } from '@/layouts/AuthLayout'
import { ProtectedRoute } from '@/components/ProtectedRoute'

import { LandingPage } from '@/pages/LandingPage'
import { LoginPage } from '@/pages/LoginPage'
import { RegisterPage } from '@/pages/RegisterPage'
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { FarmCreatePage } from '@/pages/FarmCreatePage'
import { SoilInputPage } from '@/pages/SoilInputPage'
import { WeatherPage } from '@/pages/WeatherPage'
import { CropRecommendationPage } from '@/pages/CropRecommendationPage'
import { RecommendationDetailPage } from '@/pages/RecommendationDetailPage'
import { ModelLabPage } from '@/pages/ModelLabPage'
import { RiskPage } from '@/pages/RiskPage'
import { HistoryPage } from '@/pages/HistoryPage'
import { RoadmapPage } from '@/pages/RoadmapPage'
import { CropDoctorPage } from '@/pages/CropDoctorPage'
import { AIAssistantPage } from '@/pages/AIAssistantPage'
import { SettingsPage } from '@/pages/SettingsPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />

        <Route element={<AuthLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        </Route>

        <Route
          path="/app"
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="farms/new" element={<FarmCreatePage />} />
          <Route path="soil" element={<SoilInputPage />} />
          <Route path="weather" element={<WeatherPage />} />
          <Route path="crop-recommendation" element={<CropRecommendationPage />} />
          <Route path="crop-recommendation/:cropName" element={<RecommendationDetailPage />} />
          <Route path="explanation" element={<CropRecommendationPage />} />
          <Route path="model-lab" element={<ModelLabPage />} />
          <Route path="risk" element={<RiskPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="assistant" element={<AIAssistantPage />} />
          <Route path="crop-doctor" element={<CropDoctorPage />} />
          <Route path="roadmap" element={<RoadmapPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
