-- 증거 설명은 content 컬럼에만 저장 (text=본문, photo/chat=설명). description 컬럼 제거.
ALTER TABLE public.case_evidence DROP COLUMN IF EXISTS description;
