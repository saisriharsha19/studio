import { Pool } from 'pg';
import Database from 'better-sqlite3';
import path from 'path';

// Unified interface for our database client
export interface DbClient {
  query: <T extends Record<string, any>>(sql: string, params?: any[]) => Promise<T[]>;
  run: (sql: string, params?: any[]) => Promise<{ rowCount: number }>;
  exec: (sql: string) => Promise<void>;
}

// Global variable to hold our database client
declare global {
  var dbClient: DbClient | undefined;
}

function createPostgresClient(): DbClient {
  if (!process.env.DATABASE_URL) {
    throw new Error('DATABASE_URL is not set for PostgreSQL client');
  }
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
  });

  // Postgres uses $1, $2, etc. This function converts SQL with '?' placeholders.
  const formatSql = (sql: string) => {
    let i = 0;
    return sql.replace(/\?/g, () => `$${++i}`);
  };

  return {
    query: async <T extends Record<string, any>>(sql: string, params: any[] = []): Promise<T[]> => {
      const { rows } = await pool.query<T>(formatSql(sql), params);
      return rows;
    },
    run: async (sql: string, params: any[] = []): Promise<{ rowCount: number }> => {
      const result = await pool.query(formatSql(sql), params);
      return { rowCount: result.rowCount ?? 0 };
    },
    exec: async (sql: string): Promise<void> => {
      await pool.query(sql);
    },
  };
}

function createSqliteClient(): DbClient {
  const db = new Database(path.join(process.cwd(), 'prompt_library.db'));
  db.pragma('journal_mode = WAL');

  return {
    query: async <T extends Record<string, any>>(sql: string, params: any[] = []): Promise<T[]> => {
      return db.prepare(sql).all(...params) as T[];
    },
    run: async (sql: string, params: any[] = []): Promise<{ rowCount: number }> => {
      const info = db.prepare(sql).run(...params);
      return { rowCount: info.changes };
    },
    exec: async (sql: string): Promise<void> => {
      db.exec(sql);
    },
  };
}

function initializeDbClient(): DbClient {
  // Production: Use PostgreSQL if DATABASE_URL is set
  if (process.env.DATABASE_URL) {
    console.log('Connecting to PostgreSQL...');
    return createPostgresClient();
  }
  // Development/Fallback: Use SQLite
  else {
    console.log('Using SQLite for development.');
    const client = createSqliteClient();
    
    // For SQLite, we can create tables and indexes on the fly.
    // For Postgres, migrations should be handled by a separate script/service.
    client.exec(`
      CREATE TABLE IF NOT EXISTS prompts (
        id TEXT PRIMARY KEY,
        userId TEXT NOT NULL,
        text TEXT NOT NULL,
        createdAt TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_prompts_userId ON prompts(userId);

      CREATE TABLE IF NOT EXISTS library_prompts (
        id TEXT PRIMARY KEY,
        userId TEXT NOT NULL,
        text TEXT NOT NULL,
        createdAt TEXT NOT NULL,
        summary TEXT,
        tags TEXT
      );

      CREATE TABLE IF NOT EXISTS prompt_stars (
        promptId TEXT NOT NULL,
        userId TEXT NOT NULL,
        PRIMARY KEY (promptId, userId),
        FOREIGN KEY (promptId) REFERENCES library_prompts(id) ON DELETE CASCADE
      );
      CREATE INDEX IF NOT EXISTS idx_prompt_stars_promptId ON prompt_stars(promptId);
      CREATE INDEX IF NOT EXISTS idx_prompt_stars_userId ON prompt_stars(userId);
    `);
    return client;
  }
}

// Initialize the client, reusing the connection in development environments
export const db = global.dbClient || initializeDbClient();

if (process.env.NODE_ENV !== 'production') {
  global.dbClient = db;
}
