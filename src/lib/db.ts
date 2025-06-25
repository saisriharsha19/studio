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

// Create the 'prompts' table if it doesn't already exist.
// This schema will store the prompt's ID, its text content, and creation timestamp.
db.exec(`
  CREATE TABLE IF NOT EXISTS prompts (
    id TEXT PRIMARY KEY,
    userId TEXT NOT NULL,
    text TEXT NOT NULL,
    createdAt TEXT NOT NULL
  )
`);

// Simple migration logic to add the userId column if it's missing from an older table schema.
// This prevents errors on existing databases without requiring users to delete their db file.
try {
  const columns = db.pragma('table_info(prompts)') as { name: string }[];
  const hasUserId = columns.some((col) => col.name === 'userId');

  if (!hasUserId) {
    console.log('Database migration: Adding userId column to prompts table.');
    // Add the column with a default value to satisfy the NOT NULL constraint for existing rows.
    db.exec("ALTER TABLE prompts ADD COLUMN userId TEXT NOT NULL DEFAULT 'unassigned'");
  }
} catch (error) {
  // If pragma fails, it might be because the table doesn't exist yet.
  // The CREATE TABLE above will handle that case. This is safe to ignore.
}
