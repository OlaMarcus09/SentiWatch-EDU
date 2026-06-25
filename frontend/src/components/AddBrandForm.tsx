'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Plus } from 'lucide-react';

export default function AddBrandForm() {
  const [brandName, setBrandName] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!brandName.trim()) return;

    setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/entities', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: brandName }),
      });

      const data = await response.json();
      if (data.success) {
        setBrandName('');
        // Redirect to the dashboard focused on the brand we just created
        router.push(`/?entity_id=${data.entity_id}`);
        router.refresh();
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (err) {
      alert('Could not connect to the backend server.');
    } finally {
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