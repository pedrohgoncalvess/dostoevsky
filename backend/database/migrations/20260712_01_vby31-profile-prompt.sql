-- profile prompt
-- depends: 20250506_01_aaBKK-initial-migration

ALTER TABLE "base"."profile" ADD COLUMN prompt TEXT;
