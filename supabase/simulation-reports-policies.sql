-- Supabase Storage policies for simulation-reports bucket
-- Run this in the Supabase SQL editor after creating the bucket.

-- 1. Create the bucket (idempotent)
INSERT INTO storage.buckets (id, name, public)
VALUES ('simulation-reports', 'simulation-reports', false)
ON CONFLICT (id) DO NOTHING;

-- 2. Allow authenticated users to upload to their own folder
--    Path format: {user_id}/{company_id}/final.pdf
CREATE POLICY "simulation_reports_insert_own"
ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (
  bucket_id = 'simulation-reports'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- 3. Allow authenticated users to read their own files
CREATE POLICY "simulation_reports_select_own"
ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'simulation-reports'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- 4. Allow authenticated users to update (upsert) their own files
CREATE POLICY "simulation_reports_update_own"
ON storage.objects
FOR UPDATE
TO authenticated
USING (
  bucket_id = 'simulation-reports'
  AND (storage.foldername(name))[1] = auth.uid()::text
);

-- 5. Allow authenticated users to delete their own files
CREATE POLICY "simulation_reports_delete_own"
ON storage.objects
FOR DELETE
TO authenticated
USING (
  bucket_id = 'simulation-reports'
  AND (storage.foldername(name))[1] = auth.uid()::text
);
