'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { supabase } from '@/lib/supabase';
import { AlertCircle, CheckCircle, Clock } from 'lucide-react';
import EntitySelector from '@/components/EntitySelector';
import SentimentChart from '@/components/SentimentChart';
import AddBrandForm from '@/components/AddBrandForm';

export default function Dashboard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const entityIdParam = searchParams.get('entity_id');

  const [loading, setLoading] = useState(true);
  const [allEntities, setAllEntities] = useState<any[]>([]);
  const [activeEntity, setActiveEntity] = useState<any>(null);
  const [mentions, setMentions] = useState<any[]>([]);
  const [finalRiskScore, setFinalRiskScore] = useState(0);

  useEffect(() => {
    async function loadDashboard() {
      // 1. Check Session on the Client Side (Fixes the bounce-back)
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        router.push('/login');
        return;
      }
      
      const userId = session.user.id;

      // 2. Fetch User's Entities
      const { data: entities } = await supabase
        .from('monitored_entities')
        .select('*')
        .eq('user_id', userId)
        .order('name');

      if (!entities || entities.length === 0) {
        setAllEntities([]);
        setLoading(false);
        return;
      }

      setAllEntities(entities);

      // 3. Set Active Entity
      const currentEntityId = entityIdParam || entities[0].id;
      const currentEntity = entities.find(e => e.id === currentEntityId) || entities[0];
      setActiveEntity(currentEntity);

      // 4. Fetch Mentions for the Active Entity
      const { data: fetchedMentions } = await supabase
        .from('mentions')
        .select(`*, sentiment_results(label, confidence)`)
        .eq('entity_id', currentEntityId)
        .order('created_at', { ascending: false });

      setMentions(fetchedMentions || []);

      // 5. Fetch Risk Score (Fixes the Vercel crash)
      const { data: riskData } = await supabase
        .from('risk_scores')
        .select('score')
        .eq('entity_id', currentEntityId)
        .order('created_at', { ascending: false })
        .limit(1)
        .single();

      setFinalRiskScore(Math.min(riskData?.score || 0, 100));
      setLoading(false);
    }

    loadDashboard();
  }, [entityIdParam, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-slate-500 animate-pulse">Loading your dashboard...</div>
      </div>
    );
  }

  if (allEntities.length === 0) {
    return (
      <div className="p-8 space-y-6">
        <AddBrandForm />
        <div className="p-12 text-center text-slate-500 bg-white rounded-2xl border border-gray-100 shadow-sm">
          Welcome to SentiWatch! Use the form above to activate tracking on your first brand.
        </div>
      </div>
    );
  }

  // Calculate chart metrics
  let positive = 0, neutral = 0, negative = 0;
  mentions.forEach(m => {
    const label = m.sentiment_results?.[0]?.label || 'neutral';
    if (label === 'positive') positive++;
    else if (label === 'negative') negative++;
    else neutral++;
  });

  return (
    <div className="space-y-8 p-8 overflow-y-auto h-full">
      <div className="flex flex-col md:flex-row gap-6">
        <div className="flex-1">
          <AddBrandForm />
        </div>
        <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm flex items-end">
          <EntitySelector entities={allEntities} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="col-span-1 md:col-span-2 bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-6">Sentiment Breakdown</h3>
          <SentimentChart positive={positive} neutral={neutral} negative={negative} />
        </div>

        <div className="col-span-1 bg-white rounded-2xl p-6 shadow-sm border border-gray-100 flex flex-col items-center justify-center relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-red-500 to-orange-400"></div>
          <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">Live Risk Index</h3>
          <div className="text-6xl font-black text-slate-800 tracking-tighter my-4">
            {finalRiskScore.toFixed(0)}<span className="text-2xl text-slate-400 font-medium">/100</span>
          </div>
          <p className="text-sm text-slate-500 text-center">
            {finalRiskScore > 60 ? 'High risk levels detected.' : finalRiskScore > 30 ? 'Elevated chatter detected.' : 'Brand reputation is healthy.'}
          </p>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden flex flex-col h-[500px]">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-slate-50/50">
          <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Recent Mentions</h3>
          <span className="text-xs font-medium bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full">
            {mentions.length} events
          </span>
        </div>
        
        <div className="overflow-y-auto flex-1 p-6">
          <div className="space-y-4">
            {mentions.length === 0 ? (
              <div className="text-center text-slate-400 py-8">No mentions found for this entity yet.</div>
            ) : (
              mentions.map((m) => {
                const sentiment = m.sentiment_results?.[0]?.label || 'neutral';
                
                return (
                  <div key={m.id} className="flex gap-4 p-4 rounded-xl border border-gray-100 hover:border-blue-100 hover:shadow-sm transition-all bg-white group">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{m.source}</span>
                        <span className="text-gray-300">•</span>
                        <span className="text-xs text-slate-400 flex items-center">
                          <Clock className="w-3 h-3 mr-1" />
                          {new Date(m.created_at).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})}
                        </span>
                      </div>
                      <p className="text-slate-700 text-sm leading-relaxed">{m.content}</p>
                      {m.url && (
                        <a href={m.url} target="_blank" rel="noreferrer" className="text-xs text-blue-500 hover:underline inline-block pt-1">
                          View original trace content →
                        </a>
                      )}
                    </div>

                    <div className={`self-start px-2.5 py-1 rounded-full text-xs font-bold tracking-wide border flex items-center shadow-2xs ${
                      sentiment === 'negative' ? 'bg-red-50 text-red-700 border-red-100' :
                      sentiment === 'positive' ? 'bg-green-50 text-green-700 border-green-100' :
                      'bg-slate-50 text-slate-600 border-slate-100'
                    }`}>
                      {sentiment === 'negative' && <AlertCircle className="w-3.5 h-3.5 mr-1 text-red-500" />}
                      {sentiment === 'positive' && <CheckCircle className="w-3.5 h-3.5 mr-1 text-green-500" />}
                      {sentiment.toUpperCase()}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}