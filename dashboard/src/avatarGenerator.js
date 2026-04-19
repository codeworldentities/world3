/**
 * Procedural avatar generator - creates unique visual identity for each entity
 * Based on entity ID to ensure consistency across sessions
 */

function hashCode(str) {
  let hash = 0;
  const s = String(str);
  for (let i = 0; i < s.length; i++) {
    const char = s.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return hash;
}

function pseudoRand(seed) {
  const x = Math.sin(seed * 12.9898 + seed * 78.233) * 43758.5453;
  return x - Math.floor(x);
}

export function generateAvatarPattern(entityId, size = 80) {
  // Create a deterministic "hash" from entity ID
  const hash = Math.abs(hashCode(entityId));
  
  // Color palette variations
  const colorPalettes = [
    ['#00d4ff', '#0099ff', '#0055ff'], // Cyan-Blue
    ['#ff00ff', '#ff0099', '#ff0055'], // Magenta-Pink
    ['#00ff99', '#00ff55', '#00ff00'], // Green
    ['#ffff00', '#ffcc00', '#ff9900'], // Yellow-Orange
    ['#ff5500', '#ff2200', '#ff0000'], // Red-Orange
    ['#00ffff', '#00aaff', '#0088ff'], // Cyan variations
    ['#ff88ff', '#ff55ff', '#ff22ff'], // Purple variations
    ['#88ff00', '#55ff00', '#22ff00'], // Lime variations
  ];
  
  const paletteIdx = hash % colorPalettes.length;
  const palette = colorPalettes[paletteIdx];
  
  // Pattern styles
  const styles = ['geometric', 'constellation', 'pulse', 'blocks', 'waves'];
  const styleIdx = Math.floor(hash * 100) % styles.length;
  const style = styles[styleIdx];
  
  // Generate canvas-compatible SVG pattern
  return {
    seed: entityId,
    palette,
    style,
    primaryColor: palette[0],
    secondaryColor: palette[1],
    accentColor: palette[2],
    patternSvg: generatePatternSVG(entityId, palette, style, size),
  };
}

function generatePatternSVG(entityId, palette, style, size) {
  const hash = Math.abs(hashCode(entityId));
  const rand = (seed) => {
    const x = Math.sin(seed * 12.9898 + seed * 78.233) * 43758.5453;
    return x - Math.floor(x);
  };
  
  let svg = `<svg width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">`;
  svg += `<rect width="${size}" height="${size}" fill="${palette[1]}" opacity="0.15"/>`;
  
  if (style === 'geometric') {
    // Create geometric shapes
    for (let i = 0; i < 5; i++) {
      const x = (rand(hash + i * 100) * size) | 0;
      const y = (rand(hash + i * 100 + 1) * size) | 0;
      const r = (rand(hash + i * 100 + 2) * (size / 6)) | 0;
      const color = palette[i % palette.length];
      svg += `<circle cx="${x}" cy="${y}" r="${r}" fill="${color}" opacity="0.7"/>`;
    }
    // Add connecting lines
    for (let i = 0; i < 3; i++) {
      const x1 = (rand(hash + i * 200) * size) | 0;
      const y1 = (rand(hash + i * 200 + 1) * size) | 0;
      const x2 = (rand(hash + i * 200 + 2) * size) | 0;
      const y2 = (rand(hash + i * 200 + 3) * size) | 0;
      svg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${palette[i % palette.length]}" stroke-width="2" opacity="0.5"/>`;
    }
  } else if (style === 'constellation') {
    // Star-like pattern
    const points = [];
    for (let i = 0; i < 7; i++) {
      points.push({
        x: (rand(hash + i * 50) * size) | 0,
        y: (rand(hash + i * 50 + 1) * size) | 0,
      });
    }
    // Draw stars
    points.forEach((p, i) => {
      svg += `<circle cx="${p.x}" cy="${p.y}" r="3" fill="${palette[i % palette.length]}"/>`;
    });
    // Connect near neighbors
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const dist = Math.hypot(points[i].x - points[j].x, points[i].y - points[j].y);
        if (dist < size * 0.4 && rand(hash + i * j) > 0.5) {
          svg += `<line x1="${points[i].x}" y1="${points[i].y}" x2="${points[j].x}" y2="${points[j].y}" stroke="${palette[(i + j) % palette.length]}" stroke-width="1" opacity="0.4"/>`;
        }
      }
    }
  } else if (style === 'pulse') {
    // Concentric circles
    for (let i = 0; i < 4; i++) {
      const r = ((i + 1) * size) / 8;
      svg += `<circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${palette[i % palette.length]}" stroke-width="2" opacity="0.6"/>`;
    }
    // Center dot
    svg += `<circle cx="${size / 2}" cy="${size / 2}" r="4" fill="${palette[0]}"/>`;
  } else if (style === 'blocks') {
    // Blocky pattern (like minecraft)
    for (let i = 0; i < 16; i++) {
      const row = (i / 4) | 0;
      const col = i % 4;
      if (rand(hash + i) > 0.3) {
        const x = col * (size / 4);
        const y = row * (size / 4);
        svg += `<rect x="${x}" y="${y}" width="${size / 4}" height="${size / 4}" fill="${palette[(row + col) % palette.length]}" opacity="0.7"/>`;
      }
    }
  } else if (style === 'waves') {
    // Wavy pattern
    for (let i = 0; i < 4; i++) {
      const offset = ((i * size) / 4) | 0;
      const freq = 0.02 + rand(hash + i * 10) * 0.01;
      let d = `M${offset} 0`;
      for (let x = offset; x < size + offset; x += 2) {
        const y = (Math.sin(x * freq) * (size / 6) + size / 2) | 0;
        d += ` L${x} ${y}`;
      }
      svg += `<path d="${d}" stroke="${palette[i % palette.length]}" stroke-width="3" fill="none" opacity="0.6"/>`;
    }
  }
  
  svg += `</svg>`;
  return svg;
}

/**
 * Draw avatar on canvas context
 */
export function drawAvatar(ctx, x, y, size, entityId, typeColor) {
  const avatar = generateAvatarPattern(entityId, size);
  
  // Save context state
  ctx.save();
  
  // Draw background circle with type color
  ctx.beginPath();
  ctx.arc(x, y, size / 2, 0, Math.PI * 2);
  ctx.fillStyle = typeColor || avatar.primaryColor;
  ctx.globalAlpha = 0.8;
  ctx.fill();
  
  // Add gradient overlay
  const grad = ctx.createRadialGradient(x - size / 4, y - size / 4, 0, x, y, size / 2);
  grad.addColorStop(0, 'rgba(255,255,255, 0.3)');
  grad.addColorStop(1, 'rgba(0,0,0,0.2)');
  ctx.fillStyle = grad;
  ctx.fill();
  
  ctx.globalAlpha = 1;
  
  // Draw unique pattern inside avatar
  const hash = Math.abs(hashCode(entityId));
  const rand = (seed) => pseudoRand(seed);
  
  // Draw geometric pattern (circles and lines)
  const patternCount = 3 + (hash % 2);
  for (let i = 0; i < patternCount; i++) {
    const angle = (i / patternCount) * Math.PI * 2 + (hash % 100) / 100;
    const distance = (size / 3) * (0.4 + rand(hash + i * 100) * 0.5);
    const px = x + Math.cos(angle) * distance;
    const py = y + Math.sin(angle) * distance;
    const r = (size / 8) * (0.6 + rand(hash + i * 100 + 1) * 0.4);
    
    ctx.beginPath();
    ctx.arc(px, py, r, 0, Math.PI * 2);
    ctx.fillStyle = avatar.palette[i % avatar.palette.length];
    ctx.globalAlpha = 0.7;
    ctx.fill();
  }
  
  // Draw connecting lines
  if (hash % 2 === 0) {
    for (let i = 0; i < patternCount - 1; i++) {
      const angle1 = (i / patternCount) * Math.PI * 2 + (hash % 100) / 100;
      const angle2 = ((i + 1) / patternCount) * Math.PI * 2 + (hash % 100) / 100;
      const distance = (size / 3) * (0.4 + rand(hash + i * 100) * 0.5);
      
      const x1 = x + Math.cos(angle1) * distance;
      const y1 = y + Math.sin(angle1) * distance;
      const x2 = x + Math.cos(angle2) * distance;
      const y2 = y + Math.sin(angle2) * distance;
      
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = avatar.palette[i % avatar.palette.length];
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.4;
      ctx.stroke();
    }
  }
  
  ctx.globalAlpha = 1;
  
  // Border ring
  ctx.beginPath();
  ctx.arc(x, y, size / 2, 0, Math.PI * 2);
  ctx.strokeStyle = avatar.primaryColor;
  ctx.lineWidth = 2;
  ctx.globalAlpha = 0.9;
  ctx.stroke();
  
  ctx.restore();
}

/**
 * Draw role badge on avatar
 */
export function drawRoleBadge(ctx, x, y, size, role, level = 1) {
  const badgeSize = size * 0.35;
  const badgeX = x + size / 2 - badgeSize / 2;
  const badgeY = y + size / 2 - badgeSize / 2;
  
  // Background
  ctx.fillStyle = '#1c2128';
  ctx.strokeStyle = '#30363d';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(badgeX, badgeY, badgeSize / 2, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  
  // Border glow
  ctx.strokeStyle = 'rgba(88, 166, 255, 0.5)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(badgeX, badgeY, badgeSize / 2 + 1, 0, Math.PI * 2);
  ctx.stroke();
  
  // Role text (abbreviated)
  const roleText = getRoleAbbr(role);
  ctx.fillStyle = '#58a6ff';
  ctx.font = `bold ${Math.max(9, badgeSize * 0.4)}px monospace`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(roleText, badgeX, badgeY);
}

function getRoleAbbr(role) {
  const abbrs = {
    'Developer': 'DEV',
    'Senior': 'SEN',
    'Intern': 'INT',
    'AI Copilot': 'AI',
    'Refactorer': 'REF',
    'Bug': 'BUG',
    'Web Scout': 'WEB',
  };
  return abbrs[role] || role.substring(0, 3).toUpperCase();
}

/**
 * Get profile card data for entity
 */
export function getProfileCard(entity, typeInfo) {
  return {
    id: entity.id,
    name: entity.dev_name || `#${entity.id}`,
    type: entity.type,
    icon: typeInfo?.icon || '❓',
    color: typeInfo?.color || '#888',
    level: entity.level || 1,
    energy: entity.energy || 50,
    stats: {
      influence: entity.influence || 0,
      commits: entity.commits || 0,
      language_count: entity.languages?.length || 0,
    },
  };
}
