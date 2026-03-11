-- 기존 DB: case_evidence_review → case_evidence_rebuttal, reviewer_user_id → rebutter_user_id
-- 새 DB: judge_schema가 이미 case_evidence_rebuttal을 만들므로 이 블록은 스킵됨
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'case_evidence_review'
  ) THEN
    -- 기존 정책 제거
    DROP POLICY IF EXISTS "case_evidence_review_select_own_case" ON public.case_evidence_review;
    DROP POLICY IF EXISTS "case_evidence_review_insert_reviewer" ON public.case_evidence_review;
    DROP POLICY IF EXISTS "case_evidence_review_update_reviewer" ON public.case_evidence_review;

    -- 테이블·컬럼·인덱스 이름 변경
    ALTER TABLE public.case_evidence_review RENAME TO case_evidence_rebuttal;
    ALTER TABLE public.case_evidence_rebuttal RENAME COLUMN reviewer_user_id TO rebutter_user_id;

    DROP INDEX IF EXISTS idx_case_evidence_review_evidence_id;
    DROP INDEX IF EXISTS idx_case_evidence_review_reviewer;
    CREATE INDEX IF NOT EXISTS idx_case_evidence_rebuttal_evidence_id ON public.case_evidence_rebuttal(evidence_id);
    CREATE INDEX IF NOT EXISTS idx_case_evidence_rebuttal_rebutter ON public.case_evidence_rebuttal(rebutter_user_id);

    -- RLS 재적용
    ALTER TABLE public.case_evidence_rebuttal ENABLE ROW LEVEL SECURITY;
    CREATE POLICY "case_evidence_rebuttal_select_own_case"
      ON public.case_evidence_rebuttal FOR SELECT TO authenticated
      USING (
        EXISTS (
          SELECT 1 FROM public.case_evidence ce
          JOIN public.cases c ON c.id = ce.case_id
          WHERE ce.id = case_evidence_rebuttal.evidence_id
            AND (c.created_by = auth.uid() OR c.counterpart_id = auth.uid())
        )
      );
    CREATE POLICY "case_evidence_rebuttal_insert_rebutter"
      ON public.case_evidence_rebuttal FOR INSERT TO authenticated
      WITH CHECK (
        rebutter_user_id = auth.uid()
        AND EXISTS (
          SELECT 1 FROM public.case_evidence ce
          JOIN public.cases c ON c.id = ce.case_id
          WHERE ce.id = case_evidence_rebuttal.evidence_id
            AND (c.created_by = auth.uid() OR c.counterpart_id = auth.uid())
        )
      );
    CREATE POLICY "case_evidence_rebuttal_update_rebutter"
      ON public.case_evidence_rebuttal FOR UPDATE TO authenticated
      USING (rebutter_user_id = auth.uid())
      WITH CHECK (rebutter_user_id = auth.uid());
  END IF;
END $$;
