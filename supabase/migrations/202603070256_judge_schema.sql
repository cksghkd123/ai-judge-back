-- Judge 플로우용 스키마 (Step 0)
-- Supabase 로컬: supabase db reset 또는 supabase start 시 자동 적용

-- 1. cases 테이블 (없으면 생성, 있으면 확장)
CREATE TABLE IF NOT EXISTS cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  created_by uuid NOT NULL,
  title text NOT NULL,
  description text NOT NULL,
  issue text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE cases ADD COLUMN IF NOT EXISTS invite_token text;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS counterpart_id uuid;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS creator_evidence_complete boolean NOT NULL DEFAULT false;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS counterparty_evidence_complete boolean NOT NULL DEFAULT false;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS judgment_content text;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS fault_ratio_creator int;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS fault_ratio_counterparty int;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS judged_at timestamptz;

ALTER TABLE cases ADD CONSTRAINT fault_ratio_creator_range CHECK (fault_ratio_creator IS NULL OR (fault_ratio_creator >= 0 AND fault_ratio_creator <= 100));
ALTER TABLE cases ADD CONSTRAINT fault_ratio_counterparty_range CHECK (fault_ratio_counterparty IS NULL OR (fault_ratio_counterparty >= 0 AND fault_ratio_counterparty <= 100));

CREATE UNIQUE INDEX IF NOT EXISTS idx_cases_invite_token ON cases(invite_token) WHERE invite_token IS NOT NULL;

-- 2. case_evidence
CREATE TABLE IF NOT EXISTS case_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  type text NOT NULL CHECK (type IN ('text', 'chat', 'photo')),
  content text,
  file_path text,
  description text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_case_evidence_case_id ON case_evidence(case_id);
CREATE INDEX IF NOT EXISTS idx_case_evidence_user_id ON case_evidence(user_id);

-- 3. case_evidence_rebuttal (상대 증거에 대한 반박)
CREATE TABLE IF NOT EXISTS case_evidence_rebuttal (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_id uuid NOT NULL REFERENCES case_evidence(id) ON DELETE CASCADE,
  rebutter_user_id uuid NOT NULL,
  accepted boolean NOT NULL,
  rebuttal text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(evidence_id, rebutter_user_id)
);

CREATE INDEX IF NOT EXISTS idx_case_evidence_rebuttal_evidence_id ON case_evidence_rebuttal(evidence_id);
CREATE INDEX IF NOT EXISTS idx_case_evidence_rebuttal_rebutter ON case_evidence_rebuttal(rebutter_user_id);