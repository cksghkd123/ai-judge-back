-- 판단 에이전트(자아) 테이블.
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
