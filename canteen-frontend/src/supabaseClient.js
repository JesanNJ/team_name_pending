import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || 'https://bxrnotfvoazmfdmqamwg.supabase.co';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4cm5vdGZ2b2F6bWZkbXFhbXdnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTE2Mjg2NTYsImV4cCI6MjEwNzIwNDY1Nn0.eEke362KfVmEy26fyDqSZmvQHy037IcCa3a99ZiEohk';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
