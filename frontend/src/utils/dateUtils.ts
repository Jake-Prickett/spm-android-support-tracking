/**
 * Simple date formatting utilities using built-in Intl.RelativeTimeFormat
 */

const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });

export function formatRelativeDate(dateString: string | null): string {
  if (!dateString) return 'Unknown';
  
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  // For very recent dates (less than a day), use hours
  if (Math.abs(diffDays) < 1) {
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    return Math.abs(diffHours) < 1 ? 'just now' : rtf.format(-diffHours, 'hour');
  }
  
  // Otherwise use days and let the formatter handle it
  return rtf.format(-diffDays, 'day');
}