-- 반박 완료 플래그: 양측 모두 완료 시 status=judging 전환용
ALTER TABLE public.cases ADD COLUMN IF NOT EXISTS creator_rebuttal_complete boolean NOT NULL DEFAULT false;
ALTER TABLE public.cases ADD COLUMN IF NOT EXISTS counterparty_rebuttal_complete boolean NOT NULL DEFAULT false;
