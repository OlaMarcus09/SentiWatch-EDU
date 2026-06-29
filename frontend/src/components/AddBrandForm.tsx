'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus } from 'lucide-react';
import { supabase } from '@/lib/supabase'; // Important: Import Supabase!

export default function AddBrandForm() {
  const [brandName, setBrandName] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!brandName.trim()) return;

    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      if (!token) {
        alert("You must be logged in to track a brand.");
        setLoading(false);
        return;
      }

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      
      const response = await fetch(`${API_BASE_URL}/entities`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ name: brandName }),
      });

      const data = await response.json();
      
      if (data.success) {
        setBrandName('');
        // Force a hard browser redirect to the new entity!
        window.location.href = `/?entity_id=${data.entity_id}`;
      } else {
        alert(`Error: ${data.detail || data.error || 'Failed to create entity'}`);
        setLoading(false);
      }
    } catch (err) {
      alert('Could not connect to the backend server. Make sure it is running.');
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm flex flex-col sm:flex-row gap-4 items-end">
      <div className="flex-1 space-y-1">
        <label className="text-xs font-bold text-gray-500 uppercase tracking-wider">Monitor a New Brand</label>
        <input
          type="text"
          placeholder="e.g. OPay, Cowrywise, PiggyVest"
          value={brandName}
          onChange={(e) => setBrandName(e.target.value)}
          disabled={loading}
          className="block w-full border border-gray-200 bg-slate-50 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 transition-all"
        />
      </div>
      <button
        type="submit"
        disabled={loading || !brandName.trim()}
        className="bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm px-5 py-2.5 rounded-xl flex items-center transition-all disabled:opacity-50 cursor-pointer h-[42px]"
      >
        <Plus className="w-4 h-4 mr-1.5" />
        {loading ? 'Ingesting Feeds...' : 'Activate Tracking'}
      </button>
    </form>
  );
}