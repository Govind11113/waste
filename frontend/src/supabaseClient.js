import { createClient } from '@supabase/supabase-js';

// Supabase project credentials from your project (cukvatydacokzyyuhtbl)
const supabaseUrl = 'https://cukvatydacokzyyuhtbl.supabase.co';
const supabaseAnonKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN1a3ZhdHlkYWNva3p5eXVodGJsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc1MTE1NzUsImV4cCI6MjA5MzA4NzU3NX0.EdEfhPmiptEmq_CGhVueiGO5wbzhg5gx6A7asyQlL_M';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);