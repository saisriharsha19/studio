
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
