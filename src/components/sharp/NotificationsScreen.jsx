import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { apiGet, apiPost } from '../../hooks/useApi';

export default function NotificationsScreen({ onBack }) {
  const { user } = useAuth();
  const [prefs, setPrefs] = useState({
    pick_alert: true,
    no_action: false,
    outcome: true,
    weekly_summary: true,
  });
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (user) {
      apiGet('/user/notifications').then(data => {
        if (data.prefs) setPrefs(data.prefs);
        setLoaded(true);
      }).catch(() => setLoaded(true));
    }
  }, [user]);

  const togglePref = async (key) => {
    const updated = { ...prefs, [key]: !prefs[key] };
    setPrefs(updated);

    if (user) {
      setSaving(true);
      try {
        await apiPost('/user/notifications', { prefs: updated });
      } catch (e) {
        console.error(e);
      } finally {
        setSaving(false);
      }
    }
  };

  return (
    <div style={{ padding: '0' }}>
      <div style={{
        padding: '20px 20px 16px', display: 'flex', alignItems: 'center', gap: '12px',
      }}>
        <button onClick={onBack} style={{
          background: 'none', border: 'none', cursor: 'pointer',
          color: 'var(--text-secondary)', padding: '4px',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </button>
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h1 style={{
            fontFamily: 'var(--font-serif)', fontSize: '22px',
            fontWeight: 600, color: 'var(--text-primary)',
          }}>Notifications</h1>
          {saving && (
            <span style={{
              fontSize: '11px', color: 'var(--blue-primary)',
              fontFamily: 'var(--font-mono)',
            }}>Saving...</span>
          )}
        </div>
      </div>

      <div style={{ padding: '0 20px' }}>
        {!user && (
          <div style={{
            borderRadius: '12px',
            padding: '12px 16px', marginBottom: '12px',
            border: '1px solid rgba(79, 134, 247, 0.2)',
            backgroundColor: 'rgba(79, 134, 247, 0.06)',
          }}>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', textAlign: 'center' }}>
              Sign in to save your notification preferences.
            </p>
          </div>
        )}

        <div style={{
          backgroundColor: 'var(--surface-1)', borderRadius: '16px',
          overflow: 'hidden', border: '1px solid var(--stroke-subtle)',
          opacity: user ? 1 : 0.6,
        }}>
          <ToggleRow
            label="Pick alerts"
            subtitle="Notified when a qualifying pick is published"
            active={prefs.pick_alert}
            onToggle={() => togglePref('pick_alert')}
            disabled={!user}
          />
          <ToggleRow
            label="No-action days"
            subtitle="Notified when the model passes on all games"
            active={prefs.no_action}
            onToggle={() => togglePref('no_action')}
            disabled={!user}
          />
          <ToggleRow
            label="Outcome results"
            subtitle="Notified when a pick is graded win or loss"
            active={prefs.outcome}
            onToggle={() => togglePref('outcome')}
            disabled={!user}
          />
          <ToggleRow
            label="Weekly summary"
            subtitle="Weekly recap of picks, passes, and performance"
            active={prefs.weekly_summary}
            onToggle={() => togglePref('weekly_summary')}
            last
            disabled={!user}
          />
        </div>

        {user && (
          <p style={{
            fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '16px',
            lineHeight: '1.5', textAlign: 'center',
          }}>
            Preferences are saved automatically to your account.
          </p>
        )}
      </div>
    </div>
  );
}

function ToggleRow({ label, subtitle, active, onToggle, last, disabled }) {
  return (
    <div style={{
      padding: '16px 20px',
      borderBottom: last ? 'none' : '1px solid var(--stroke-subtle)',
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <div>
        <div style={{
          fontSize: '14px', fontWeight: 500, color: 'var(--text-primary)',
        }}>{label}</div>
        <div style={{
          fontSize: '12px', color: 'var(--text-tertiary)', marginTop: '2px',
        }}>{subtitle}</div>
      </div>
      <button onClick={disabled ? undefined : onToggle} disabled={disabled} style={{
        width: '44px', height: '24px', borderRadius: '12px', border: 'none',
        backgroundColor: active ? 'var(--blue-primary)' : 'var(--surface-2)',
        cursor: 'pointer', position: 'relative', transition: 'background-color 0.2s',
        flexShrink: 0,
      }}>
        <div style={{
          width: '20px', height: '20px', borderRadius: '50%',
          backgroundColor: '#fff', position: 'absolute', top: '2px',
          left: active ? '22px' : '2px', transition: 'left 0.2s',
        }} />
      </button>
    </div>
  );
}
