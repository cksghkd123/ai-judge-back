-- Judge 플로우 전체 스키마 (통합)
-- claimant/respondent, case_evidence_rebuttal, judge_agents, Storage, RLS 포함.

-- ---------------------------------------------------------------------------
-- 1. cases
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  claimant_id uuid NOT NULL,
  respondent_id uuid,
  claimant_name text NOT NULL,
  claimant_address text NOT NULL,
  claimant_jobs text[] NOT NULL DEFAULT '{}'::text[],
  claimant_profile_image text,
  title text NOT NULL,
  description text NOT NULL,
  issue text NOT NULL,
  status text NOT NULL DEFAULT 'pending',
  invite_token text,
  judge_agent_id text DEFAULT 'default',
  claimant_evidence_complete boolean NOT NULL DEFAULT false,
  respondent_evidence_complete boolean NOT NULL DEFAULT false,
  claimant_rebuttal_complete boolean NOT NULL DEFAULT false,
  respondent_rebuttal_complete boolean NOT NULL DEFAULT false,
  judgment_content text,
  fault_ratio_claimant int,
  fault_ratio_respondent int,
  judged_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.cases
  ADD CONSTRAINT fault_ratio_claimant_range
  CHECK (fault_ratio_claimant IS NULL OR (fault_ratio_claimant >= 0 AND fault_ratio_claimant <= 100));

ALTER TABLE public.cases
  ADD CONSTRAINT fault_ratio_respondent_range
  CHECK (fault_ratio_respondent IS NULL OR (fault_ratio_respondent >= 0 AND fault_ratio_respondent <= 100));

CREATE UNIQUE INDEX IF NOT EXISTS idx_cases_invite_token ON public.cases(invite_token) WHERE invite_token IS NOT NULL;

-- ---------------------------------------------------------------------------
-- 2. case_evidence (description 없음, content만 사용)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.case_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id uuid NOT NULL REFERENCES public.cases(id) ON DELETE CASCADE,
  user_id uuid NOT NULL,
  type text NOT NULL CHECK (type IN ('text', 'chat', 'photo')),
  content text,
  file_path text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_case_evidence_case_id ON public.case_evidence(case_id);
CREATE INDEX IF NOT EXISTS idx_case_evidence_user_id ON public.case_evidence(user_id);

-- ---------------------------------------------------------------------------
-- 3. case_evidence_rebuttal
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.case_evidence_rebuttal (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evidence_id uuid NOT NULL REFERENCES public.case_evidence(id) ON DELETE CASCADE,
  rebutter_user_id uuid NOT NULL,
  accepted boolean NOT NULL,
  rebuttal text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(evidence_id, rebutter_user_id)
);

CREATE INDEX IF NOT EXISTS idx_case_evidence_rebuttal_evidence_id ON public.case_evidence_rebuttal(evidence_id);
CREATE INDEX IF NOT EXISTS idx_case_evidence_rebuttal_rebutter ON public.case_evidence_rebuttal(rebutter_user_id);

-- ---------------------------------------------------------------------------
-- 4. judge_agents
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.judge_agents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  persona text NOT NULL,
  judge_image text,
  style text,
  created_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.judge_agents IS '판단 에이전트.';
COMMENT ON COLUMN public.judge_agents.judge_image IS '에이전트 이미지 URL.';
COMMENT ON COLUMN public.judge_agents.style IS '판사 말투 지시';

-- ---------------------------------------------------------------------------
-- 5. Storage bucket (100MB)
-- ---------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit)
VALUES (
  'ai-judge-storage',
  'ai-judge-storage',
  false,
  104857600
)
ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 6. RLS: cases
-- ---------------------------------------------------------------------------
ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY;
CREATE POLICY "cases_select_own_or_counterparty"
  ON public.cases FOR SELECT
  TO authenticated
  USING (claimant_id = auth.uid() OR respondent_id = auth.uid());

CREATE POLICY "cases_insert_own_claimant"
  ON public.cases FOR INSERT
  TO authenticated
  WITH CHECK (claimant_id = auth.uid());

CREATE POLICY "cases_update_own_or_counterparty"
  ON public.cases FOR UPDATE
  TO authenticated
  USING (claimant_id = auth.uid() OR respondent_id = auth.uid())
  WITH CHECK (claimant_id = auth.uid() OR respondent_id = auth.uid());

-- ---------------------------------------------------------------------------
-- 7. RLS: case_evidence
-- ---------------------------------------------------------------------------
ALTER TABLE public.case_evidence ENABLE ROW LEVEL SECURITY;
CREATE POLICY "case_evidence_select_own_case"
  ON public.case_evidence FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.cases c
      WHERE c.id = case_evidence.case_id
        AND (c.claimant_id = auth.uid() OR c.respondent_id = auth.uid())
    )
  );

CREATE POLICY "case_evidence_insert_own"
  ON public.case_evidence FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = auth.uid()
    AND EXISTS (
      SELECT 1 FROM public.cases c
      WHERE c.id = case_evidence.case_id
        AND (c.claimant_id = auth.uid() OR c.respondent_id = auth.uid())
    )
  );

CREATE POLICY "case_evidence_update_own_case"
  ON public.case_evidence FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.cases c
      WHERE c.id = case_evidence.case_id
        AND (c.claimant_id = auth.uid() OR c.respondent_id = auth.uid())
    )
  );

-- ---------------------------------------------------------------------------
-- 8. RLS: case_evidence_rebuttal
-- ---------------------------------------------------------------------------
ALTER TABLE public.case_evidence_rebuttal ENABLE ROW LEVEL SECURITY;
CREATE POLICY "case_evidence_rebuttal_select_own_case"
  ON public.case_evidence_rebuttal FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.case_evidence ce
      JOIN public.cases c ON c.id = ce.case_id
      WHERE ce.id = case_evidence_rebuttal.evidence_id
        AND (c.claimant_id = auth.uid() OR c.respondent_id = auth.uid())
    )
  );

CREATE POLICY "case_evidence_rebuttal_insert_rebutter"
  ON public.case_evidence_rebuttal FOR INSERT
  TO authenticated
  WITH CHECK (
    rebutter_user_id = auth.uid()
    AND EXISTS (
      SELECT 1 FROM public.case_evidence ce
      JOIN public.cases c ON c.id = ce.case_id
      WHERE ce.id = case_evidence_rebuttal.evidence_id
        AND (c.claimant_id = auth.uid() OR c.respondent_id = auth.uid())
    )
  );

CREATE POLICY "case_evidence_rebuttal_update_rebutter"
  ON public.case_evidence_rebuttal FOR UPDATE
  TO authenticated
  USING (rebutter_user_id = auth.uid())
  WITH CHECK (rebutter_user_id = auth.uid());

-- ---------------------------------------------------------------------------
-- 9. judge_agents 시드
-- ---------------------------------------------------------------------------
INSERT INTO public.judge_agents (name, persona, judge_image, style)
VALUES
  (
    '공정한 판사',
    '당신은 제시된 사건과 양측의 증거·반박을 바탕으로 공정히 판단하는 역할입니다.',
    NULL,
    '~습니다. 와 같은 말투를 사용하세요.'
  ),
  (
    '매우 엄격한 판사',
    '당신은 매우 엄격하고 진지한 판사입니다.
법리와 원칙을 중시하며, 감정보다는 사실과 증거에 따라 판단합니다.
말투는 간결하고 단호합니다. 굉장히 깐깐한 사람으로 감정에 민감하지 않습니다. MBTI 100% T',
    NULL,
    '~합니다. ~했습니다. 와 같은 말투를 사용하세요.'
  ),
  (
    '연애전문 판사',
    '당신은 연인·부부 간 갈등을 잘 이해하는 연애(사랑싸움) 전문가입니다.
감정과 관계 맥락을 고려하면서도, 어느 쪽이 더 손해를 봤는지 공정하게 나눕니다.
말투는 공감적이면서도 결론은 분명하게 내립니다.',
    NULL,
    '~라고 생각되네요. ~인 것 같아요. 와 같은 말투를 사용하세요.'
  );
