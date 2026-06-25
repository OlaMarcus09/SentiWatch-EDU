import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Activity, BarChart3, Settings, Bell } from 'lucide-react'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'SentiWatch | Reputation Dashboard',
  description: 'Automated reputation monitoring for local businesses.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-gray-50 flex h-screen overflow-hidden`}>
        
        {/* Persistent Sidebar */}
        <aside className="w-64 bg-slate-900 text-white flex flex-col hidden md:flex">
          <div className="h-16 flex items-center px-6 border-b border-slate-800">
            <Activity className="w-6 h-6 text-blue-400 mr-2" />
            <span className="text-xl font-bold tracking-tight">SentiWatch</span>
          </div>
          
          <nav className="flex-1 py-6 px-4 space-y-2">
            <a href="#" className="flex items-center px-4 py-3 bg-blue-600/10 text-blue-400 rounded-lg font-medium">
              <BarChart3 className="w-5 h-5 mr-3" />
              Dashboard
            </a>
            <a href="#" className="flex items-center px-4 py-3 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
              <Bell className="w-5 h-5 mr-3" />
              Alert History
            </a>
            <a href="#" className="flex items-center px-4 py-3 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
              <Settings className="w-5 h-5 mr-3" />
              Settings
            </a>
          </nav>

          <div className="p-4 border-t border-slate-800">
            <div className="flex items-center">
              <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-sm font-medium">
                SME
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium">Founder Account</p>
                <p className="text-xs text-slate-400">Pro Plan</p>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col h-screen overflow-hidden">
          <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-8 z-10">
            <h2 className="text-lg font-semibold text-gray-800">Overview</h2>
            <div className="flex items-center space-x-4">
              <span className="text-sm font-medium px-3 py-1 bg-green-100 text-green-700 rounded-full">System Operational</span>
            </div>
          </header>
          
          {/* This is where your page.tsx content injects! */}
          <main className="flex-1 overflow-y-auto p-8">
            {children}
          </main>
        </div>

      </body>
    </html>
  )
}