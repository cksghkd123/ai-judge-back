-- RLS 활성화: public.cases, case_evidence, case_evidence_rebuttal
-- PostgREST로 노출된 테이블은 RLS 권장. 백엔드는 service_role로 RLS 우회.

-- 1. cases
ALTER TABLE public.cases ENABLE ROW LEVEL SECURITY;

-- 본인이 생성했거나 상대측으로 참여한 사건만 조회
CREATE POLICY "cases_select_own_or_counterpart"
  ON public.cases FOR SELECT
  TO authenticated
  USING (
    created_by = auth.uid() OR counterpart_id = auth.uid()
  );

-- 인증된 사용자는 본인을 created_by로 사건 생성 가능
CREATE POLICY "cases_insert_own"
  ON public.cases FOR INSERT
  TO authenticated
  WITH CHECK (created_by = auth.uid());

-- 본인이 생성자이거나 상대측인 경우만 수정 가능 (join, status 등)
CREATE POLICY "cases_update_own_or_counterpart"
  ON public.cases FOR UPDATE
  TO authenticated
  USING (created_by = auth.uid() OR counterpart_id = auth.uid())
  WITH CHECK (created_by = auth.uid() OR counterpart_id = auth.uid());

-- 2. case_evidence
ALTER TABLE public.case_evidence ENABLE ROW LEVEL SECURITY;

-- 본인이 참여한 사건의 증거만 조회
CREATE POLICY "case_evidence_select_own_case"
  ON public.case_evidence FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.cases c
      WHERE c.id = case_evidence.case_id
        AND (c.created_by = auth.uid() OR c.counterpart_id = auth.uid())
    )
  );

-- 본인만 증거 추가 (user_id = auth.uid()), 해당 사건에 참여한 경우만
CREATE POLICY "case_evidence_insert_own"
  ON public.case_evidence FOR INSERT
  TO authenticated
  WITH CHECK (
    user_id = auth.uid()
    AND EXISTS (
      SELECT 1 FROM public.cases c
      WHERE c.id = case_evidence.case_id
        AND (c.created_by = auth.uid() OR c.counterpart_id = auth.uid())
    )
  );

-- 본인이 참여한 사건의 증거만 수정 (본인 작성 증거 등)
CREATE POLICY "case_evidence_update_own_case"
  ON public.case_evidence FOR UPDATE
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.cases c
      WHERE c.id = case_evidence.case_id
        AND (c.created_by = auth.uid() OR c.counterpart_id = auth.uid())
    )
  );

-- 3. case_evidence_rebuttal
ALTER TABLE public.case_evidence_rebuttal ENABLE ROW LEVEL SECURITY;

-- 본인이 참여한 사건의 증거에 대한 반박만 조회
CREATE POLICY "case_evidence_rebuttal_select_own_case"
  ON public.case_evidence_rebuttal FOR SELECT
  TO authenticated
  USING (
    EXISTS (
      SELECT 1 FROM public.case_evidence ce
      JOIN public.cases c ON c.id = ce.case_id
      WHERE ce.id = case_evidence_rebuttal.evidence_id
        AND (c.created_by = auth.uid() OR c.counterpart_id = auth.uid())
    )
  );

-- 반박 작성자가 본인이고, 해당 사건 참여자일 때만 INSERT
CREATE POLICY "case_evidence_rebuttal_insert_rebutter"
  ON public.case_evidence_rebuttal FOR INSERT
  TO authenticated
  WITH CHECK (
    rebutter_user_id = auth.uid()
    AND EXISTS (
      SELECT 1 FROM public.case_evidence ce
      JOIN public.cases c ON c.id = ce.case_id
      WHERE ce.id = case_evidence_rebuttal.evidence_id
        AND (c.created_by = auth.uid() OR c.counterpart_id = auth.uid())
    )
  );

-- 반박 작성자가 본인인 경우만 UPDATE
CREATE POLICY "case_evidence_rebuttal_update_rebutter"
  ON public.case_evidence_rebuttal FOR UPDATE
  TO authenticated
  USING (rebutter_user_id = auth.uid())
  WITH CHECK (rebutter_user_id = auth.uid());
