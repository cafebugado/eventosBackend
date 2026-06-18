-- ============================================================
-- Migration 0003 — Expansão do perfil de usuário (user_profiles)
-- Cole este script no SQL Editor do painel do Supabase.
-- Equivalente exato da migration Alembic 0003_user_profile_expansao_perfil.py
-- ============================================================

-- 1. Novas colunas de dados pessoais
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS genero TEXT;
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS whatsapp TEXT;

-- 2. Coluna de provider de login (email | google | github)
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS provider TEXT;

-- 3. Novas colunas de dados profissionais
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS cargo_atual TEXT;
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS empresa TEXT;
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS area_atuacao TEXT;
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS nivel_experiencia TEXT;
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS portfolio_url TEXT;
ALTER TABLE public.user_profiles ADD COLUMN IF NOT EXISTS bio TEXT;

-- 4. CHECK constraint: idade mínima de 18 anos
--    Permite NULL (perfis antigos sem data) mas bloqueia data_nascimento < 18 anos atrás
--    em qualquer INSERT/UPDATE futuro.
ALTER TABLE public.user_profiles
  ADD CONSTRAINT ck_user_profiles_idade_minima
  CHECK (data_nascimento IS NULL OR data_nascimento <= CURRENT_DATE - INTERVAL '18 years');

-- 5. CHECK constraint: valores válidos de gênero
ALTER TABLE public.user_profiles
  ADD CONSTRAINT ck_user_profiles_genero
  CHECK (genero IS NULL OR genero IN ('Masculino', 'Feminino', 'Outro', 'Prefiro não informar'));

-- 6. CHECK constraint: valores válidos de nível de experiência
ALTER TABLE public.user_profiles
  ADD CONSTRAINT ck_user_profiles_nivel_experiencia
  CHECK (nivel_experiencia IS NULL OR nivel_experiencia IN
    ('Estagiário', 'Júnior', 'Pleno', 'Sênior', 'Especialista/Staff'));

-- 7. CHECK constraint: valores válidos de provider
ALTER TABLE public.user_profiles
  ADD CONSTRAINT ck_user_profiles_provider
  CHECK (provider IS NULL OR provider IN ('email', 'google', 'github'));

-- ============================================================
-- Para desfazer (rollback manual), execute em ordem inversa:
--
-- ALTER TABLE public.user_profiles DROP CONSTRAINT IF EXISTS ck_user_profiles_provider;
-- ALTER TABLE public.user_profiles DROP CONSTRAINT IF EXISTS ck_user_profiles_nivel_experiencia;
-- ALTER TABLE public.user_profiles DROP CONSTRAINT IF EXISTS ck_user_profiles_genero;
-- ALTER TABLE public.user_profiles DROP CONSTRAINT IF EXISTS ck_user_profiles_idade_minima;
-- ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS bio;
-- ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS portfolio_url;
-- ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS nivel_experiencia;
-- ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS area_atuacao;
-- ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS empresa;
-- ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS cargo_atual;
-- ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS provider;
-- ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS whatsapp;
-- ALTER TABLE public.user_profiles DROP COLUMN IF EXISTS genero;
-- ============================================================
