export interface ValidationResult {
  valid: boolean;
  error?: string;
  sanitizedSql?: string;
}

const FORBIDDEN_KEYWORDS = [
  'INSERT',
  'UPDATE',
  'DELETE',
  'DROP',
  'ALTER',
  'CREATE',
  'TRUNCATE',
  'MERGE',
  'EXEC',
  'EXECUTE',
  'GRANT',
  'REVOKE',
  'DENY',
  'XP_',
  'SP_',
  'INTO',
];

export function validateSelectQuery(sql: string): ValidationResult {
  if (!sql || typeof sql !== 'string') {
    return { valid: false, error: 'SQL query must be a non-empty string.' };
  }

  const trimmed = sql.trim();

  // 1. Must start with SELECT or WITH (for CTEs)
  const startsWithValidWord = /^(SELECT|WITH)\b/i.test(trimmed);
  if (!startsWithValidWord) {
    return {
      valid: false,
      error: 'Query security violation: Only SELECT and WITH (CTE) statements are permitted.',
    };
  }

  // 2. Reject SQL comment injections
  if (/--|\/\*/.test(trimmed)) {
    return {
      valid: false,
      error: 'Query security violation: SQL comments (-- or /* */) are not allowed.',
    };
  }

  // 3. Reject statement chaining with semicolons
  // Allow a trailing semicolon if it's the last character
  const strippedTrailingSemicolon = trimmed.replace(/;\s*$/, '');
  if (strippedTrailingSemicolon.includes(';')) {
    return {
      valid: false,
      error: 'Query security violation: Multiple SQL statements or statement chaining is forbidden.',
    };
  }

  // 4. Check for forbidden keywords using strict word boundaries
  const uppercaseSql = strippedTrailingSemicolon.toUpperCase();
  for (const keyword of FORBIDDEN_KEYWORDS) {
    const regex = new RegExp(`\\b${keyword}\\b`, 'i');
    if (regex.test(uppercaseSql)) {
      return {
        valid: false,
        error: `Query security violation: Forbidden keyword "${keyword}" detected. Only read-only SELECT queries are allowed.`,
      };
    }
  }

  // 5. Enforce TOP 1000 row cap if query lacks a TOP clause
  let sanitizedSql = strippedTrailingSemicolon;
  if (!/\bTOP\s+\d+/i.test(sanitizedSql) && /^SELECT\b/i.test(sanitizedSql)) {
    sanitizedSql = sanitizedSql.replace(/^SELECT\b/i, 'SELECT TOP 1000');
  }

  return {
    valid: true,
    sanitizedSql,
  };
}
