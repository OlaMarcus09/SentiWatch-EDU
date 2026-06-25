import { supabase } from '@/lib/supabase';
import { AlertCircle, CheckCircle, Clock, ShieldAlert, MessageSquare, ShieldCheck } from 'lucide-react';
import EntitySelector from '@/components/EntitySelector';
import SentimentChart from '@/components/SentimentChart';
import AddBrandForm from '@/components/AddBrandForm';

export const revalidate = 0;

export default async function Dashboard({
  searchParams,
}: {
  searchParams: Promise<{ entity_id?: string }>;
}) {
  const resolvedParams = await searchParams;

  // 1. Fetch all monitored entities for the switcher dropdown
  const { data: allEntities } = await supabase.from('monitored_entities').select('*').order('name');
  if (!allEntities || allEntities.length === 0) {
    return (
      <div className="space-y-6">
        <AddBrandForm />
        <div className="p-12 text-center text-slate-500 bg-white rounded-2xl border border-gray-100 shadow-sm">
          No brands are currently being monitored. Use the form above to activate tracking on your first brand.
        </div>
      </div>
    );
  }

  // 2. Select active entity (defaults to first item if none selected in URL)
  const activeEntityId = resolvedParams.entity_id || allEntities[0].id;
  const entity = allEntities.find((e) => e.id === activeEntityId) || allEntities[0];

  // 3. Fetch all mentions linked to this specific entity
  const { data: mentions } = await supabase
    .from('mentions')
    .select(`
      id,
      source,
      content,
      created_at,
      url,
      sentiment_results ( label, confidence )
    `)
    .eq('entity_id', entity.id)
    .order('created_at', { ascending: false });

  // 4. Compute metrics right here on the server
  const totalMentions = mentions?.length || 0;
  
  let positiveCount = 0;
  let neutralCount = 0;
  let negativeCount = 0;
  let accumulatedRisk = 0;

  mentions?.forEach((m) => {
    const label = m.sentiment_results?.[0]?.label || 'neutral';
    if (label === 'positive') positiveCount++;
    else if (label === 'neutral') neutralCount++;
    else if (label === 'negative') {
      negativeCount++;
      // Replicate the exact mathematical risk weight assigned by backend risk engine
      if (m.source.includes('News')) accumulatedRisk += 30;
      else if (m.source.includes('Maps')) accumulatedRisk += 20;
      else accumulatedRisk += 10;
    }
  });

  const finalRiskScore = Math.min(accumulatedRisk, 100);

  return (
    <div className="space-y-8">
      
      {/* Top Banner Widget incorporating Entity Selector component */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 shadow-md flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Welcome to SentiWatch</h1>
          <p className="text-slate-400 text-sm mt-0.5">Monitoring brand reputation flags across Nigerian digital ecosystem feeds.</p>
        </div>
        <div>
          <EntitySelector entities={allEntities} />
        </div>
      </div>

      {/* Onboarding Input Stream Form Component */}
      <AddBrandForm />

      {/* Metric Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Risk Card */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm flex items-center space-x-4">
          <div className={`p-4 rounded-xl ${finalRiskScore >= 60 ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'}`}>
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Reputation Risk Index</p>
            <p className="text-2xl font-bold text-gray-900 mt-0.5">{finalRiskScore}/100</p>
            <p className={`text-xs font-semibold mt-1 ${finalRiskScore >= 60 ? 'text-red-500' : 'text-green-500'}`}>
              {finalRiskScore >= 60 ? '🚨 Critical State reached' : '✓ Secure standing'}
            </p>
          </div>
        </div>

        {/* Volume Card */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm flex items-center space-x-4">
          <div className="p-4 rounded-xl bg-blue-50 text-blue-600">
            <MessageSquare className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Total Mentions Evaluated</p>
            <p className="text-2xl font-bold text-gray-900 mt-0.5">{totalMentions}</p>
            <p className="text-xs text-slate-400 font-medium mt-1">Aggregated tracking index</p>
          </div>
        </div>

        {/* Security / System Integrity Card */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm flex items-center space-x-4">
          <div className="p-4 rounded-xl bg-teal-50 text-teal-600">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-500">Incident Alert Guard</p>
            <p className="text-2xl font-bold text-gray-900 mt-0.5">Active</p>
            <p className="text-xs text-slate-400 font-medium mt-1">Resend notification dispatcher armed</p>
          </div>
        </div>
      </div>

      {/* Analytics Visualization and Live Feed Split Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Sentiment breakdown Donut visual block */}
        <div className="bg-white rounded-2xl p-6 border border-gray-100 shadow-sm h-full flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-gray-800 text-lg">Sentiment Analytics</h3>
            <p className="text-xs text-gray-400 mt-0.5">AI breakdown distribution mapping</p>
          </div>
          <div className="py-4">
            <SentimentChart positive={positiveCount} neutral={neutralCount} negative={negativeCount} />
          </div>
        </div>

        {/* Mentions Listing Main Stream Feed */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden flex flex-col">
          <div className="p-6 border-b border-gray-50 bg-white">
            <h3 className="font-bold text-gray-800 text-lg">System Flag Streams</h3>
            <p className="text-xs text-gray-400 mt-0.5">Real-time chronologically sorted ingestion listing</p>
          </div>
          
          <div className="divide-y divide-gray-100 overflow-y-auto max-h-[400px]">
            {!mentions || mentions.length === 0 ? (
              <div className="p-12 text-center text-gray-400 text-sm">No digital signals parsed yet for this brand profile.</div>
            ) : (
              mentions.map((m: any) => {
                const sentiment = m.sentiment_results?.[0]?.label || 'neutral';
                return (
                  <div key={m.id} className="p-5 hover:bg-slate-50/50 transition-colors flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="space-y-1.5 max-w-xl">
                      <div className="flex items-center space-x-2.5">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-blue-600 bg-blue-50/80 px-2 py-0.5 rounded-md border border-blue-100">
                          {m.source}
                        </span>
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