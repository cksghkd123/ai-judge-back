INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES (
  'ai-judge-storage',
  'ai-judge-storage',
  false,
  104857600
)
ON CONFLICT (id) DO NOTHING;
-- file_size_limit 104857600 = 100MB
