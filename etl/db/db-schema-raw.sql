-- noinspection SqlNoDataSourceInspectionForFile
-- Database defs for raw timeseries (history) data for Smart Emission
DROP SCHEMA IF EXISTS smartem_raw CASCADE;
CREATE SCHEMA smartem_raw;

-- Raw device realtime output timeseries (history) table - data one2one from rawsensor api
DROP TABLE IF EXISTS smartem_raw.timeseries CASCADE;
CREATE TABLE smartem_raw.timeseries (
  gid serial,
  unique_id character varying (16) not null,
  insert_time timestamp with time zone default current_timestamp,
  device_id integer not null,
  day integer not null,
  hour integer not null,
  data json,
  complete boolean default false,
  PRIMARY KEY (gid)
) WITHOUT OIDS;

DROP INDEX IF EXISTS timeseries_uid_idx;
CREATE UNIQUE INDEX timeseries_uid_idx ON smartem_raw.timeseries USING btree (unique_id) ;

-- ETL progress tabel, houdt bij voor laatst ingelezen timeseries is per device .
DROP TABLE IF EXISTS smartem_raw.harvester_progress CASCADE;
CREATE TABLE smartem_raw.harvester_progress (
  gid serial,
  insert_time timestamp with time zone default current_timestamp,
  unique_id character varying (16) not null,
  device_id integer not null,
  day integer not null,
  hour integer not null,
  PRIMARY KEY (gid)
) WITHOUT OIDS;

-- TRIGGER to update checkpointing by storing last day/hour for each device
-- Thus the Harvester always knows where to start from when running
CREATE OR REPLACE FUNCTION harvester_progress_update() RETURNS TRIGGER AS $harvester_progress_update$
  BEGIN
        --
        -- Set the progress for the device id to the last day+hour harvested
        -- make use of the special variable TG_OP to work out the operation.
        --

        IF (TG_OP = 'INSERT') THEN
          -- Delete possibly existing entry for device
          DELETE FROM smartem_raw.harvester_progress WHERE device_id = NEW.device_id;

          -- Always insert new entry for device with latest harvested day/hour
          INSERT INTO smartem_raw.harvester_progress (unique_id, device_id, day, hour)
              VALUES (NEW.unique_id, NEW.device_id, NEW.day, NEW.hour);
        END IF;

        RETURN NULL; -- result is ignored since this is an AFTER trigger
    END;

$harvester_progress_update$ LANGUAGE plpgsql;

--exec
DROP TRIGGER IF EXISTS harvester_progress_update ON smartem_raw.timeseries;

--exec
CREATE TRIGGER harvester_progress_update AFTER INSERT ON smartem_raw.timeseries
    FOR EACH ROW EXECUTE PROCEDURE harvester_progress_update();
