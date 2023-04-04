from datetime import datetime, timedelta, timezone


def volume_query(addresses, days=60, end=None):
    if end is None:
        t_end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        t_end = datetime.fromtimestamp(end, tz=timezone.utc)
    print("    end date:", t_end)
    t_start = t_end - timedelta(days=days)

    if isinstance(addresses, str):
        addresses = [addresses]

    queries = []
    for address in addresses:
        q = """
            {
              swapVolumeSnapshots(
                orderBy: timestamp,
                orderDirection: desc,
                where:
                  {
                    pool: "%s"
                    period: "86400"
                    timestamp_gte: %d
                    timestamp_lte: %d
                  }
              )
              {
                volume
                timestamp
              }
            }
        """ % (
            address.lower(),
            int(t_start.timestamp()),
            int(t_end.timestamp()),
        )
        queries.append(q)

    return queries


def process_volume_result(results, days):
    volumes = []
    for r in results:
        snapshots = r["swapVolumeSnapshots"]
        num_snapshots = len(snapshots)

        if num_snapshots < days:
            print(f"Warning: only {num_snapshots}/{days} days of pool volume returned")

        vol = [float(s["volume"]) for s in snapshots]
        volumes.append(vol)

    return volumes
