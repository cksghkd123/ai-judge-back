-- claimant_address 를 nullable로 변경 (기존 운영/개발 DB 업그레이드용)
ALTER TABLE public.cases
  ALTER COLUMN claimant_address DROP NOT NULL;

