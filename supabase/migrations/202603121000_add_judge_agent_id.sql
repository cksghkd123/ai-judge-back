-- 사건별 판단 에이전트(자아) 선택용
ALTER TABLE public.cases ADD COLUMN IF NOT EXISTS judge_agent_id text DEFAULT 'default';
