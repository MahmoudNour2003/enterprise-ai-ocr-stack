type LogLevel = 'info' | 'warn' | 'error' | 'debug';

function log(level: LogLevel, message: string, meta?: Record<string, unknown>) {
  const timestamp = new Date().toISOString();
  const output = {
    timestamp,
    level,
    message,
    ...meta,
  };
  
  if (level === 'error') {
    console.error(JSON.stringify(output));
  } else if (level === 'warn') {
    console.warn(JSON.stringify(output));
  } else {
    console.log(JSON.stringify(output));
  }
}

export const logger = {
  info: (msg: string, meta?: Record<string, unknown>) => log('info', msg, meta),
  warn: (msg: string, meta?: Record<string, unknown>) => log('warn', msg, meta),
  error: (msg: string, meta?: Record<string, unknown>) => log('error', msg, meta),
  debug: (msg: string, meta?: Record<string, unknown>) => log('debug', msg, meta),
};
