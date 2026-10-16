CREATE TABLE IF NOT EXISTS daymark_daily (
  owner_id text NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  day date NOT NULL CHECK(day BETWEEN DATE '2000-01-01' AND DATE '2100-12-31'),
  status text NOT NULL CHECK(status IN ('missing','partial','complete')),
  coding_seconds double precision,github_seconds double precision,chatgpt_seconds double precision,
  orca_seconds double precision,reading_seconds double precision,other_seconds double precision,
  synced_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(owner_id,day),
  CHECK(
    (status='missing' AND coding_seconds IS NULL AND github_seconds IS NULL AND chatgpt_seconds IS NULL AND orca_seconds IS NULL AND reading_seconds IS NULL AND other_seconds IS NULL)
    OR
    (status IN ('partial','complete') AND coding_seconds BETWEEN 0 AND 86400 AND github_seconds BETWEEN 0 AND 86400 AND chatgpt_seconds BETWEEN 0 AND 86400 AND orca_seconds BETWEEN 0 AND 86400 AND reading_seconds BETWEEN 0 AND 86400 AND other_seconds BETWEEN 0 AND 86400 AND coding_seconds IS NOT NULL AND github_seconds IS NOT NULL AND chatgpt_seconds IS NOT NULL AND orca_seconds IS NOT NULL AND reading_seconds IS NOT NULL AND other_seconds IS NOT NULL AND coding_seconds+github_seconds+chatgpt_seconds+orca_seconds+reading_seconds+other_seconds<=86400)
  )
);
REVOKE ALL ON daymark_daily FROM PUBLIC;
