import Database from 'better-sqlite3';
import path from 'path';

// Enhance the global object to include our database instance
declare global {
  var db: Database.Database | undefined;
}

// Define the path for the SQLite database file
const dbPath = path.join(process.cwd(), 'prompt_library.db');

// Initialize the database connection, reusing the existing connection in development
// to avoid issues with Next.js hot-reloading.
export const db = global.db || new Database(dbPath);

if (process.env.NODE_ENV !== 'production') {
  global.db = db;
}

// Enable Write-Ahead Logging for better concurrency
db.pragma('journal_mode = WAL');

// Create the 'prompts' table for history if it doesn't already exist.
db.exec(`
  CREATE TABLE IF NOT EXISTS prompts (
    id TEXT PRIMARY KEY,
    userId TEXT NOT NULL,
    text TEXT NOT NULL,
    createdAt TEXT NOT NULL
  )
`);

// Create the 'library_prompts' table for the official library if it doesn't already exist.
db.exec(`
  CREATE TABLE IF NOT EXISTS library_prompts (
    id TEXT PRIMARY KEY,
    userId TEXT NOT NULL,
    text TEXT NOT NULL,
    createdAt TEXT NOT NULL,
    tags TEXT
  )
`);

// Create the 'prompt_stars' table to track user stars
db.exec(`
  CREATE TABLE IF NOT EXISTS prompt_stars (
    promptId TEXT NOT NULL,
    userId TEXT NOT NULL,
    PRIMARY KEY (promptId, userId),
    FOREIGN KEY (promptId) REFERENCES library_prompts(id) ON DELETE CASCADE
  )
`);

// Simple migration logic for the 'prompts' table.
try {
  const columns = db.pragma('table_info(prompts)') as { name: string }[];
  const hasUserId = columns.some((col) => col.name === 'userId');

  if (!hasUserId) {
    console.log('Database migration: Adding userId column to prompts table.');
    db.exec("ALTER TABLE prompts ADD COLUMN userId TEXT NOT NULL DEFAULT 'unassigned'");
  }
} catch (error) {
  // Safe to ignore if table doesn't exist yet.
}

// Simple migration logic for the 'library_prompts' table.
try {
  const columns = db.pragma('table_info(library_prompts)') as { name: string }[];
  if (!columns.some((col) => col.name === 'userId')) {
    console.log('Database migration: Adding userId column to library_prompts table.');
    db.exec("ALTER TABLE library_prompts ADD COLUMN userId TEXT NOT NULL DEFAULT 'unassigned'");
  }
  if (!columns.some((col) => col.name === 'tags')) {
    console.log('Database migration: Adding tags column to library_prompts table.');
    db.exec("ALTER TABLE library_prompts ADD COLUMN tags TEXT");
  }
} catch (error) {
  // Safe to ignore if table doesn't exist yet.
}
