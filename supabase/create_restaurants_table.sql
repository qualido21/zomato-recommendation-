-- Run this in Supabase SQL Editor before uploading data.
-- Dashboard → SQL Editor → New query → paste & run.

create table if not exists restaurants (
  id            integer primary key,
  name          text    not null,
  city          text    not null default '',
  location      text    not null default '',
  cuisines      jsonb   not null default '[]',
  rating        real,
  votes         integer not null default 0,
  approx_cost   integer,
  budget_tier   text    not null default 'medium',
  rest_type     text    not null default '',
  book_table    boolean not null default false,
  online_order  boolean not null default false,
  listed_type   text    not null default ''
);

-- Index for fast locality lookups (FilterEngine queries location column)
create index if not exists idx_restaurants_location on restaurants (lower(location));

-- Index for rating sort
create index if not exists idx_restaurants_rating on restaurants (rating desc nulls last);

-- Enable Row Level Security (allow public read-only access)
alter table restaurants enable row level security;

create policy "Public read access"
  on restaurants for select
  using (true);
