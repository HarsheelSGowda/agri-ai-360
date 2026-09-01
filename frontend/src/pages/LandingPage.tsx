import { Link } from 'react-router-dom'
import {
  Leaf,
  Sprout,
  FlaskConical,
  CloudSun,
  BrainCircuit,
  TrendingUp,
  DollarSign,
  Stethoscope,
  MessageCircle,
  ArrowRight,
  Gauge,
} from 'lucide-react'

const capabilities = [
  { icon: Sprout, title: 'Crop Intelligence', desc: 'ML-driven crop suitability ranking from real soil and climate signals.', live: true },
  { icon: FlaskConical, title: 'Soil Intelligence', desc: 'N-P-K, pH and soil-type analysis with an explainable health score.', live: true },
  { icon: CloudSun, title: 'Weather Intelligence', desc: 'Live conditions and short-range forecast feeding the recommendation engine.', live: true },
  { icon: BrainCircuit, title: 'Explainable AI', desc: 'SHAP-powered "why this crop" breakdown for every recommendation.', live: true },
  { icon: TrendingUp, title: 'Yield Prediction', desc: 'Forecast expected yield per acre for the recommended crop.', live: false },
  { icon: DollarSign, title: 'Profit Intelligence', desc: 'Estimate input cost vs. expected return.', live: false },
  { icon: Stethoscope, title: 'Disease Detection', desc: 'Computer-vision leaf disease diagnosis from a photo.', live: false },
  { icon: MessageCircle, title: 'AI Assistant', desc: 'Conversational farm advisor grounded in your own data.', live: false },
]

const techStack = ['Random Forest', 'XGBoost', 'SHAP', 'FastAPI', 'React', 'PostgreSQL']

export function LandingPage() {
  return (
    <div className="min-h-screen bg-forest-950 text-white">
      <Nav />
      <Hero />
      <Problem />
      <Solution />
      <Capabilities />
      <HowItWorks />
      <TechStack />
      <CTA />
      <Footer />
    </div>
  )
}

function Nav() {
  return (
    <nav className="sticky top-0 z-40 border-b border-white/5 bg-forest-950/70 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-500 to-lime-400">
            <Leaf size={18} className="text-forest-950" />
          </div>
          <span className="text-lg font-bold tracking-tight">AgriAI 360</span>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/login" className="px-4 py-2 text-sm font-medium text-white/70 hover:text-white">
            Log in
          </Link>
          <Link to="/register" className="btn-primary px-5 py-2 text-sm">
            Get Started
          </Link>
        </div>
      </div>
    </nav>
  )
}

function Hero() {
  return (
    <section className="relative overflow-hidden bg-grid px-6 pb-24 pt-20">
      <div className="pointer-events-none absolute left-1/2 top-0 h-[32rem] w-[32rem] -translate-x-1/2 rounded-full bg-emerald-500/20 blur-[140px]" />
      <div className="relative z-10 mx-auto max-w-5xl text-center">
        <span className="mb-6 inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-1.5 text-xs font-medium text-emerald-300">
          <span className="h-1.5 w-1.5 animate-pulse-glow rounded-full bg-emerald-400" />
          Explainable AI Decision Support · Final-Year CSE Research Project
        </span>
        <h1 className="glow-text text-5xl font-bold leading-[1.05] tracking-tight sm:text-7xl">
          INTELLIGENCE FOR
          <br />
          <span className="bg-gradient-to-r from-emerald-400 to-lime-300 bg-clip-text text-transparent">EVERY ACRE.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-white/60">
          AI-powered crop recommendations built from soil, weather and environmental intelligence.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link to="/register" className="btn-primary px-8 py-3.5 text-base">
            Analyze My Farm <ArrowRight size={18} />
          </Link>
          <Link to="/app/model-lab" className="btn-secondary px-8 py-3.5 text-base">
            Explore AI
          </Link>
        </div>
      </div>

      <HeroVisual />
    </section>
  )
}

function HeroVisual() {
  return (
    <div className="relative z-10 mx-auto mt-16 max-w-5xl">
      <div className="glass-card grid grid-cols-2 gap-4 p-6 md:grid-cols-4">
        {[
          { label: 'Soil Health', value: '82/100', icon: FlaskConical },
          { label: 'Weather', value: '28°C', icon: CloudSun },
          { label: 'AI Suitability', value: '94.2%', icon: Gauge },
          { label: 'Top Crop', value: 'Cotton', icon: Sprout },
        ].map(({ label, value, icon: Icon }) => (
          <div key={label} className="flex flex-col items-center gap-2 rounded-xl bg-white/5 py-6 text-center">
            <Icon size={20} className="text-emerald-400" />
            <span className="text-xl font-bold text-white">{value}</span>
            <span className="text-[11px] uppercase tracking-wider text-white/40">{label}</span>
          </div>
        ))}
      </div>
      <p className="mt-3 text-center text-[11px] text-white/30">Illustrative preview — sign in to run analysis on your own farm data.</p>
    </div>
  )
}

function Problem() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <div className="grid gap-10 md:grid-cols-2">
        <div>
          <span className="text-xs uppercase tracking-widest text-rose-300/70">The Problem</span>
          <h2 className="mt-3 text-3xl font-bold tracking-tight">Traditional crop selection depends on guesswork.</h2>
          <ul className="mt-6 space-y-3 text-white/60">
            {['Experience', 'Guesswork', 'Limited soil knowledge', 'Unpredictable weather'].map((item) => (
              <li key={item} className="flex items-center gap-3">
                <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <span className="text-xs uppercase tracking-widest text-emerald-300/70">The Solution</span>
          <h2 className="mt-3 text-3xl font-bold tracking-tight">AgriAI 360 combines data, ML and explainability.</h2>
          <ul className="mt-6 space-y-3 text-white/60">
            {['Soil', 'Weather', 'Location', 'Machine Learning', 'Explainable AI'].map((item) => (
              <li key={item} className="flex items-center gap-3">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  )
}

function Solution() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-8">
      <div className="glass-card flex flex-wrap items-center justify-center gap-3 px-8 py-10 text-center text-sm font-medium text-white/70 sm:gap-6 sm:text-base">
        <span>Input</span>
        <ArrowRight size={16} className="text-emerald-400" />
        <span>AI</span>
        <ArrowRight size={16} className="text-emerald-400" />
        <span>Explanation</span>
        <ArrowRight size={16} className="text-emerald-400" />
        <span>Decision</span>
      </div>
    </section>
  )
}

function Capabilities() {
  return (
    <section className="mx-auto max-w-6xl px-6 py-20">
      <div className="mb-12 text-center">
        <span className="text-xs uppercase tracking-widest text-emerald-300/70">AI Capabilities</span>
        <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">A complete farm decision-support platform</h2>
      </div>
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {capabilities.map(({ icon: Icon, title, desc, live }) => (
          <div key={title} className="glass-card glass-card-hover flex flex-col gap-3 p-5">
            <div className="flex items-center justify-between">
              <span className="rounded-lg bg-emerald-400/10 p-2 text-emerald-400">
                <Icon size={18} />
              </span>
              {!live && (
                <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-white/40">
                  Roadmap
                </span>
              )}
            </div>
            <h3 className="font-semibold text-white">{title}</h3>
            <p className="text-xs leading-relaxed text-white/50">{desc}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function HowItWorks() {
  return (
    <section className="mx-auto max-w-4xl px-6 py-12 text-center">
      <span className="text-xs uppercase tracking-widest text-emerald-300/70">How It Works</span>
      <div className="mt-6 flex flex-wrap items-center justify-center gap-4 text-lg font-semibold text-white/80">
        <span>Input</span>
        <ArrowRight className="text-emerald-400" size={20} />
        <span>AI</span>
        <ArrowRight className="text-emerald-400" size={20} />
        <span>Explanation</span>
        <ArrowRight className="text-emerald-400" size={20} />
        <span>Decision</span>
      </div>
    </section>
  )
}

function TechStack() {
  return (
    <section className="mx-auto max-w-5xl px-6 py-16">
      <div className="glass-card flex flex-wrap items-center justify-center gap-x-10 gap-y-4 px-8 py-8">
        {techStack.map((t) => (
          <span key={t} className="text-sm font-medium tracking-wide text-white/50">
            {t}
          </span>
        ))}
      </div>
    </section>
  )
}

function CTA() {
  return (
    <section className="mx-auto max-w-4xl px-6 py-24 text-center">
      <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">Start Your Farm Analysis</h2>
      <p className="mx-auto mt-4 max-w-xl text-white/50">
        Create a free account, add your farm's soil and location data, and get an explainable AI crop recommendation in minutes.
      </p>
      <Link to="/register" className="btn-primary mt-8 inline-flex px-8 py-3.5 text-base">
        Analyze My Farm <ArrowRight size={18} />
      </Link>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-white/5 px-6 py-10 text-center text-xs text-white/30">
      AgriAI 360 — Explainable AI-Powered Intelligent Crop Recommendation and Farm Decision Support System. Final-year CSE major project.
    </footer>
  )
}
