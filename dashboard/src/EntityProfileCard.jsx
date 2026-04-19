import React, { useEffect, useRef } from 'react';
import { drawAvatar, drawRoleBadge } from './avatarGenerator';

/**
 * Entity Profile Card Component
 * Displays avatar, name, role, and stats
 */
export function EntityProfileCard({ entity, typeInfo, avatarPattern, onClose }) {
  const canvasRef = useRef(null);

  // Draw avatar on canvas when mounted or updated
  useEffect(() => {
    if (!canvasRef.current) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const size = 140;
    
    ctx.clearRect(0, 0, size, size);
    
    // Draw avatar
    drawAvatar(ctx, size / 2, size / 2, size, entity.id, typeInfo?.color);
    
    // Draw role badge
    if (entity.role) {
      drawRoleBadge(ctx, size / 2 - size / 4, size / 2 - size / 4, size / 2, entity.role, entity.level || 1);
    }
  }, [entity, typeInfo]);

  if (!entity) return null;

  const getRoleIcon = (role) => {
    const icons = {
      'Team Lead': '👑',
      'Senior': '⭐',
      'Developer': '👨‍💻',
      'Intern': '🌱',
      'AI Copilot': '🤖',
      'Refactorer': '♻️',
      'Bug': '🐛',
      'Web Scout': '🌐',
      'Freelancer': '📋',
      'Architect': '🏛️',
      'Reviewer': '👀',
      'Tester': '✓',
      'Judge': '⚖️',
      'Teacher': '📚',
    };
    return icons[role] || '👤';
  };

  const getLevelEmoji = (level) => {
    if (level >= 15) return '🏆'; // Legend
    if (level >= 12) return '💎'; // Diamond
    if (level >= 9) return '🥇'; // Gold
    if (level >= 6) return '🥈'; // Silver
    if (level >= 3) return '🥉'; // Bronze
    return '📈';
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h2 style={styles.title}>{entity.dev_name || `Entity #${entity.id}`}</h2>
        <button style={styles.closeBtn} onClick={onClose}>✕</button>
      </div>

      <div style={styles.content}>
        {/* Avatar Section */}
        <div style={styles.avatarSection}>
          <div style={styles.avatarContainer}>
            <canvas
              ref={canvasRef}
              width="140"
              height="140"
              style={styles.avatarCanvas}
            />
          </div>

          {/* Role Badge */}
          <div style={{
            ...styles.roleBadge,
            backgroundColor: typeInfo?.color || '#888',
          }}>
            <span style={styles.roleIcon}>{getRoleIcon(entity.role)}</span>
            <span style={styles.roleText}>{entity.role || 'Developer'}</span>
          </div>

          {/* Level Badge */}
          <div style={styles.levelBadge}>
            <span style={styles.levelEmoji}>{getLevelEmoji(entity.level || 1)}</span>
            <span style={styles.levelText}>Level {entity.level || 1}</span>
          </div>
        </div>

        {/* Stats Section */}
        <div style={styles.statsSection}>
          <h3 style={styles.statsTitle}>Stats</h3>

          <div style={styles.statRow}>
            <span style={styles.statLabel}>Energy</span>
            <div style={styles.statBar}>
              <div
                style={{
                  ...styles.statFill,
                  width: `${Math.min(100, (entity.energy <= 1 ? entity.energy * 100 : entity.energy))}%`,
                  backgroundColor: (entity.energy <= 1 ? entity.energy * 100 : entity.energy) > 60 ? '#3fb950' : (entity.energy <= 1 ? entity.energy * 100 : entity.energy) > 30 ? '#d29922' : '#f85149',
                }}
              />
            </div>
            <span style={styles.statValue}>{Math.round(entity.energy <= 1 ? entity.energy * 100 : entity.energy)}%</span>
          </div>

          <div style={styles.statRow}>
            <span style={styles.statLabel}>Influence</span>
            <span style={{...styles.statValue, color: '#58a6ff'}}>
              {Math.round(entity.influence || 0)}
            </span>
          </div>

          <div style={styles.statRow}>
            <span style={styles.statLabel}>Commits</span>
            <span style={{...styles.statValue, color: '#3fb950'}}>
              {entity.commits || 0}
            </span>
          </div>

          <div style={styles.statRow}>
            <span style={styles.statLabel}>Languages</span>
            <span style={{...styles.statValue, color: '#bc8cff'}}>
              {entity.languages?.length || 0}
            </span>
          </div>

          {entity.languages && entity.languages.length > 0 && (
            <div style={styles.languagesList}>
              {entity.languages.map((lang, i) => (
                <span key={i} style={styles.languageTag}>
                  {lang}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Info Section */}
        {entity.instinct && (
          <div style={styles.infoSection}>
            <h3 style={styles.infoTitle}>Motivation</h3>
            <p style={styles.infoValue}>{entity.instinct}</p>
          </div>
        )}

        {entity.group_name && (
          <div style={styles.groupSection}>
            <h3 style={styles.groupTitle}>Team</h3>
            <p style={styles.groupName}>{entity.group_name}</p>
          </div>
        )}

        {entity.web_source && (
          <div style={styles.webSection}>
            <h3 style={styles.webTitle}>Researching</h3>
            <p style={{...styles.webValue, color: '#7ee7ff'}}>
              🌐 {entity.web_source.toUpperCase()} Portal
            </p>
            {entity.web_mission_until && (
              <p style={styles.webMission}>
                Mission until tick {entity.web_mission_until}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const styles = {
  container: {
    position: 'fixed',
    right: '20px',
    top: '100px',
    width: '340px',
    maxHeight: '80vh',
    backgroundColor: '#0d1117',
    border: '2px solid #30363d',
    borderRadius: '8px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6)',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 1000,
    backdropFilter: 'blur(10px)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '16px',
    borderBottom: '1px solid #30363d',
    backgroundColor: '#161b22',
  },
  title: {
    margin: 0,
    fontSize: '18px',
    color: '#c9d1d9',
    fontWeight: '600',
  },
  closeBtn: {
    backgroundColor: 'transparent',
    border: 'none',
    color: '#8b949e',
    fontSize: '20px',
    cursor: 'pointer',
    padding: '0',
    width: '24px',
    height: '24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '4px',
    transition: 'all 0.2s',
  },
  content: {
    overflow: 'auto',
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
    padding: '16px',
  },
  avatarSection: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '12px',
  },
  avatarContainer: {
    width: '140px',
    height: '140px',
    borderRadius: '50%',
    border: '3px solid #30363d',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.5)',
    position: 'relative',
    overflow: 'hidden',
  },
  avatarCanvas: {
    display: 'block',
    imageRendering: 'crisp-edges',
  },
  avatarSvg: {
    filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))',
  },
  roleBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    borderRadius: '20px',
    color: '#fff',
    fontSize: '14px',
    fontWeight: '600',
  },
  roleIcon: {
    fontSize: '16px',
  },
  roleText: {
    whiteSpace: 'nowrap',
  },
  levelBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    backgroundColor: '#1c2128',
    border: '1px solid #30363d',
    borderRadius: '16px',
    color: '#c9d1d9',
    fontSize: '12px',
  },
  levelEmoji: {
    fontSize: '14px',
  },
  levelText: {
    whiteSpace: 'nowrap',
  },
  statsSection: {
    backgroundColor: '#1c2128',
    border: '1px solid #30363d',
    borderRadius: '6px',
    padding: '12px',
  },
  statsTitle: {
    margin: '0 0 12px 0',
    fontSize: '13px',
    color: '#8b949e',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  statRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '10px',
    fontSize: '13px',
  },
  statLabel: {
    color: '#8b949e',
    minWidth: '80px',
  },
  statBar: {
    flex: 1,
    height: '6px',
    backgroundColor: '#0d1117',
    borderRadius: '3px',
    overflow: 'hidden',
    border: '1px solid #30363d',
  },
  statFill: {
    height: '100%',
    background: 'linear-gradient(90deg, currentColor 0%, rgba(255,255,255,0.3))',
    transition: 'width 0.3s',
  },
  statValue: {
    color: '#c9d1d9',
    fontSize: '12px',
    fontWeight: '600',
    minWidth: '40px',
    textAlign: 'right',
  },
  languagesList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
    marginTop: '10px',
  },
  languageTag: {
    display: 'inline-block',
    padding: '4px 8px',
    backgroundColor: '#0d1117',
    border: '1px solid #30363d',
    borderRadius: '4px',
    color: '#bc8cff',
    fontSize: '11px',
    fontWeight: '500',
  },
  infoSection: {
    backgroundColor: '#1c2128',
    border: '1px solid #30363d',
    borderRadius: '6px',
    padding: '12px',
  },
  infoTitle: {
    margin: '0 0 8px 0',
    fontSize: '12px',
    color: '#8b949e',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  infoValue: {
    margin: 0,
    fontSize: '13px',
    color: '#c9d1d9',
  },
  groupSection: {
    backgroundColor: '#1c2128',
    border: '1px solid #30363d',
    borderRadius: '6px',
    padding: '12px',
  },
  groupTitle: {
    margin: '0 0 8px 0',
    fontSize: '12px',
    color: '#8b949e',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  groupName: {
    margin: 0,
    fontSize: '13px',
    color: '#58a6ff',
    fontWeight: '500',
  },
  webSection: {
    backgroundColor: '#1c2128',
    border: '2px solid #7ee7ff',
    borderRadius: '6px',
    padding: '12px',
  },
  webTitle: {
    margin: '0 0 8px 0',
    fontSize: '12px',
    color: '#7ee7ff',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  webValue: {
    margin: '0 0 6px 0',
    fontSize: '13px',
  },
  webMission: {
    margin: 0,
    fontSize: '11px',
    color: '#8b949e',
    fontStyle: 'italic',
  },
};
