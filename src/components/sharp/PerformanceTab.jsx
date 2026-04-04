import { useState, useEffect } from 'react';
import { Capacitor } from '@capacitor/core';
import { useAuth } from '../../hooks/useAuth';
import { getAuthToken } from '../../hooks/useApi';
import { useSport } from '../../hooks/useSport';
import { trackEvent } from '../../utils/eventTracker';
import UnifiedDashboard from './UnifiedDashboard';
import DashboardTab from './DashboardTab';
import FreeTierDashboard from './FreeTierDashboard';
import OnboardingCard from './OnboardingCard';

const API_ROOT = Capacitor.isNativePlatform() ? 'https://app.sharppicks.ai' : '';

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function fetchCardBlob(endpoint) {
  const token = getAuthToken();
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(`${API_ROOT}${endpoint}`, { headers, credentials: 'include' });
  if (!res.ok) throw new Error(`Failed to fetch card: ${res.status}`);
  return res.blob();
}

async function nativeShare(blob, filename) {
  const { Filesystem, Directory } = await import('@capacitor/filesystem');
  const { Share } = await import('@capacitor/share');

  const base64 = await blobToBase64(blob);
  const file = await Filesystem.writeFile({
    path: filename,
    data: base64,
    directory: Directory.Cache,
  });

  await Share.share({
    title: 'Sharp Picks Weekly Recap',
    text: 'Beat the market, not the scoreboard.\n\nsharppicks.ai',
    url: file.uri,
    dialogTitle: 'Share your results',
  });

  try {
    await Filesystem.deleteFile({ path: filename, directory: Directory.Cache });
  } catch {}
}

function webShare(blob, filename) {
  const file = new File([blob], filename, { type: 'image/png' });
  if (navigator.share && navigator.canShare?.({ files: [file] })) {
    return navigator.share({
      title: 'Sharp Picks Weekly Recap',
      text: 'Beat the market, not the scoreboard. sharppicks.ai',
      files: [file],
    });
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function PerformanceTab({ onNavigate, initialView, onViewConsumed }) {
  const { user } = useAuth();
  const { sport } = useSport();
  const isPro = user && (user.is_premium || user.subscription_status === 'active' || user.subscription_status === 'trial' || user.founding_member);
  const [view, setView] = useState(initialView || (isPro ? 'yours' : 'model'));
  const [sharePreview, setSharePreview] = useState(null);
  const [shareLoading, setShareLoading] = useState(null);

  useEffect(() => { trackEvent('view_model_performance'); }, []);

  useEffect(() => {
    if (initialView) {
      setView(initialView);
      if (onViewConsumed) onViewConsumed();
    }
  }, [initialView]);

  const handleShareTap = async (endpoint, filename) => {
    setShareLoading(endpoint);
    try {
      const blob = await fetchCardBlob(endpoint);
      const previewUrl = URL.createObjectURL(blob);
      setSharePreview({ blob, previewUrl, filename });
    } catch (e) {
      console.error('Failed to generate card:', e);
    } finally {
      setShareLoading(null);
    }
  };

  const handleShareConfirm = async () => {
    if (!sharePreview) return;
    const { blob, filename, previewUrl } = sharePreview;
    try {
      if (Capacitor.isNativePlatform()) {
        await nativeShare(blob, filename);
      } else {
        await webShare(blob, filename);
      }
    } catch (e) {
      console.error('Share failed:', e);
    }
    URL.revokeObjectURL(previewUrl);
    setSharePreview(null);
  };

  const handleShareCancel = () => {
    if (sharePreview?.previewUrl) URL.revokeObjectURL(sharePreview.previewUrl);
    setSharePreview(null);
  };

  if (!isPro) {
    return (
      <div style={{ padding: '0', paddingBottom: '100px' }}>
        <div style={{ padding: '0 20px', marginTop: '12px', marginBottom: '16px' }}>
          <div style={{
            display: 'flex',
            backgroundColor: 'var(--surface-1)',
            borderRadius: '10px',
            padding: '3px',
            border: '1px solid var(--stroke-subtle)',
          }}>
            <ToggleButton active={view === 'yours'} onClick={() => setView('yours')} label="Your Results" />
            <ToggleButton active={view === 'model'} onClick={() => setView('model')} label="Model" />
          </div>
        </div>
        {view === 'model' ? (
          <DashboardTab onNavigate={onNavigate} embedded />
        ) : (
          <FreeResultsEmptyState />
        )}
      </div>
    );
  }

  return (
    <div style={{ padding: '0', paddingBottom: '100px' }}>

      <div style={{ padding: '0 20px', marginTop: '12px', marginBottom: '16px' }}>
        <OnboardingCard cardId="results" title="YOUR RECORD">
          Every signal tracked with full transparency. The equity curve shows cumulative performance. CLV measures whether the model beat the closing line. Discipline score tracks your selectivity vs. the industry average.
        </OnboardingCard>
        <div style={{
          display: 'flex',
          backgroundColor: 'var(--surface-1)',
          borderRadius: '10px',
          padding: '3px',
          border: '1px solid var(--stroke-subtle)',
        }}>
          <ToggleButton active={view === 'yours'} onClick={() => setView('yours')} label="Your Results" />
          <ToggleButton active={view === 'model'} onClick={() => setView('model')} label="Model" />
        </div>
      </div>

      {view === 'yours' ? (
        <UnifiedDashboard embedded />
      ) : (
        <DashboardTab onNavigate={onNavigate} embedded />
      )}

      <div style={{ padding: '0 20px', marginTop: '16px', display: 'flex', gap: '10px' }}>
        <ShareButton
          label="Share Results"
          loading={shareLoading === '/api/cards/user-results'}
          onClick={() => handleShareTap(`/api/cards/user-results?sport=${sport}`, 'sharppicks-results.png')}
        />
        <ShareButton
          label="Share Weekly"
          loading={shareLoading === `/api/cards/weekly-report?sport=${sport}`}
          onClick={() => handleShareTap(`/api/cards/weekly-report?sport=${sport}`, 'sharppicks-weekly.png')}
        />
      </div>

      {sharePreview && (
        <SharePreviewModal
          previewUrl={sharePreview.previewUrl}
          onShare={handleShareConfirm}
          onCancel={handleShareCancel}
        />
      )}
    </div>
  );
}


function ShareButton({ label, loading, onClick }) {
  return (
    <button onClick={onClick} disabled={loading} style={{
      flex: 1, padding: '12px', borderRadius: '10px', fontWeight: 600, fontSize: '12px',
      fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)',
      background: 'var(--surface-1)', border: '1px solid var(--stroke-subtle)',
      cursor: loading ? 'default' : 'pointer', opacity: loading ? 0.6 : 1,
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
    }}>
      {loading ? (
        <span style={{ fontSize: '11px' }}>Generating...</span>
      ) : (
        <>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8"/>
            <polyline points="16 6 12 2 8 6"/>
            <line x1="12" y1="2" x2="12" y2="15"/>
          </svg>
          {label}
        </>
      )}
    </button>
  );
}


function SharePreviewModal({ previewUrl, onShare, onCancel }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      backgroundColor: 'rgba(0,0,0,0.85)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '16px',
    }} onClick={onCancel}>
      <div style={{
        maxWidth: '400px', width: '100%',
        display: 'flex', flexDirection: 'column', gap: '16px',
      }} onClick={e => e.stopPropagation()}>
        <img
          src={previewUrl}
          alt="Share card preview"
          style={{
            width: '100%', borderRadius: '12px',
            boxShadow: '0 12px 40px rgba(0,0,0,0.5)',
          }}
        />
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={onShare} style={{
            flex: 1, padding: '14px', borderRadius: '10px',
            backgroundColor: '#5A9E72', border: 'none',
            color: '#fff', fontSize: '15px', fontWeight: 700,
            fontFamily: 'var(--font-sans)', cursor: 'pointer',
          }}>Share</button>
          <button onClick={onCancel} style={{
            flex: 1, padding: '14px', borderRadius: '10px',
            backgroundColor: 'transparent',
            border: '1px solid rgba(255,255,255,0.15)',
            color: 'var(--text-secondary)', fontSize: '15px', fontWeight: 600,
            fontFamily: 'var(--font-sans)', cursor: 'pointer',
          }}>Cancel</button>
        </div>
      </div>
    </div>
  );
}


function FreeResultsEmptyState() {
  const trackingFeatures = [
    'Equity curve with cumulative P&L',
    'Discipline score vs industry average',
    'Capital preserved from passed picks',
    'Model vs off-model comparison',
  ];
  return (
    <div style={{ padding: '0 20px' }}>
      <div style={{
        backgroundColor: 'var(--surface-1)', borderRadius: '16px',
        border: '1px solid var(--stroke-subtle)', padding: '32px 24px',
        textAlign: 'center',
      }}>
        <div style={{ marginBottom: '20px', opacity: 0.4 }}>
          <svg width="32" height="32" viewBox="0 0 500 500">
            <rect x="150" y="100" width="60" height="300" rx="30" fill="#e8ecf0" />
            <rect x="290" y="100" width="60" height="300" rx="30" fill="#e8ecf0" />
            <rect x="150" y="420" width="200" height="20" rx="10" fill="#5A9E72" />
          </svg>
        </div>
        <p style={{
          fontFamily: 'var(--font-serif)', fontSize: '15px', fontWeight: 500,
          color: 'var(--text-primary)', lineHeight: '1.6', marginBottom: '8px',
        }}>Start tracking to see your equity curve.</p>
        <p style={{
          fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.6',
          maxWidth: '280px', margin: '0 auto 20px',
        }}>
          Log your bets, see your P&L in real time, and measure your discipline against the industry average.
        </p>

        <div style={{
          textAlign: 'left', marginBottom: '20px',
          paddingTop: '16px', borderTop: '1px solid var(--stroke-subtle)',
        }}>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '9px', fontWeight: 600,
            letterSpacing: '1.5px', textTransform: 'uppercase',
            color: 'var(--text-tertiary)', marginBottom: '10px',
          }}>TRACKING UNLOCKS:</div>
          {trackingFeatures.map(f => (
            <div key={f} style={{
              display: 'flex', alignItems: 'center', gap: '8px',
              padding: '4px 0',
            }}>
              <span style={{ color: 'var(--color-signal)', fontSize: '10px' }}>&#10003;</span>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{f}</span>
            </div>
          ))}
        </div>

        <p style={{
          fontSize: '12px', color: 'var(--text-tertiary)', marginBottom: '16px',
        }}>Personal tracking is a Pro feature.</p>

        <button onClick={() => window.open('https://sharppicks.ai/#pricing', '_blank')} style={{
          width: '100%', padding: '12px', borderRadius: '6px',
          border: '1.5px solid #5A9E72', background: 'transparent',
          color: '#5A9E72', fontFamily: 'var(--font-mono)',
          fontSize: '12px', fontWeight: 600, letterSpacing: '1px',
          cursor: 'pointer', textAlign: 'center',
        }}>View Plans at sharppicks.ai</button>

        <p style={{
          fontFamily: 'var(--font-serif)', fontStyle: 'italic',
          fontSize: '12px', color: 'var(--text-tertiary)',
          marginTop: '16px', lineHeight: '1.5',
        }}>"The record you keep is the edge you build."</p>
      </div>
    </div>
  );
}

function ToggleButton({ active, onClick, label }) {
  return (
    <button onClick={onClick} style={{
      flex: 1,
      padding: '8px 0',
      fontSize: '13px',
      fontWeight: 600,
      fontFamily: 'var(--font-sans)',
      border: 'none',
      borderRadius: '8px',
      cursor: 'pointer',
      backgroundColor: active ? '#5A9E72' : 'transparent',
      color: active ? '#fff' : 'var(--text-tertiary)',
      transition: 'all 0.2s',
    }}>
      {label}
    </button>
  );
}


