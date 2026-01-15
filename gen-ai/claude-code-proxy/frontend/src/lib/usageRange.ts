export type UsagePeriod = 'day' | 'week' | 'month';
export type BucketType = 'minute' | 'hour' | 'day' | 'week' | 'month';

export const KST_TIME_ZONE = 'Asia/Seoul';

const KST_OFFSET_MS = 9 * 60 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;

export interface ResolvedRange {
  startTime: Date;
  endTime: Date;
  rangeDays: number;
  startDate: string;
  endDate: string;
}

export function resolvePeriodRange(period: UsagePeriod, now: Date = new Date()): ResolvedRange {
  const { year, month, day } = getKstParts(now);
  const endTime = now;
  let startTime: Date;
  let rangeDays: number;

  if (period === 'day') {
    startTime = kstDateFromParts(year, month, day);
    rangeDays = 1;
  } else if (period === 'week') {
    rangeDays = 7;
    startTime = new Date(endTime.getTime() - (rangeDays - 1) * DAY_MS);
  } else {
    rangeDays = 30;
    startTime = new Date(endTime.getTime() - (rangeDays - 1) * DAY_MS);
  }

  return {
    startTime,
    endTime,
    rangeDays,
    startDate: toKstDateString(startTime),
    endDate: toKstDateString(endTime),
  };
}

export function resolveCustomRange(
  startDate: string,
  endDate: string
): ResolvedRange | null {
  const startParts = parseDateString(startDate);
  const endParts = parseDateString(endDate);
  if (!startParts || !endParts) return null;

  const startDayMs = Date.UTC(startParts.year, startParts.month - 1, startParts.day);
  const endDayMs = Date.UTC(endParts.year, endParts.month - 1, endParts.day);
  if (endDayMs < startDayMs) return null;

  const rangeDays = Math.max(1, Math.floor((endDayMs - startDayMs) / DAY_MS) + 1);

  return {
    startTime: kstDateFromParts(startParts.year, startParts.month, startParts.day),
    endTime: kstDateFromParts(endParts.year, endParts.month, endParts.day + 1),
    rangeDays,
    startDate,
    endDate,
  };
}

export function selectBucketType(rangeDays: number): BucketType {
  if (rangeDays <= 2) return 'hour';
  if (rangeDays <= 45) return 'day';
  return 'week';
}

export function toKstDateString(date: Date): string {
  const kst = new Date(date.getTime() + KST_OFFSET_MS);
  const year = kst.getUTCFullYear();
  const month = String(kst.getUTCMonth() + 1).padStart(2, '0');
  const day = String(kst.getUTCDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function formatKstDate(date: Date): string {
  return date.toLocaleDateString('en-US', {
    timeZone: KST_TIME_ZONE,
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatKstDateTime(date: Date): string {
  return date.toLocaleString('en-US', {
    timeZone: KST_TIME_ZONE,
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function kstDateFromParts(year: number, month: number, day: number): Date {
  return new Date(Date.UTC(year, month - 1, day) - KST_OFFSET_MS);
}

function getKstParts(date: Date) {
  const kst = new Date(date.getTime() + KST_OFFSET_MS);
  return {
    year: kst.getUTCFullYear(),
    month: kst.getUTCMonth() + 1,
    day: kst.getUTCDate(),
    dayOfWeek: kst.getUTCDay(),
  };
}

function parseDateString(value: string) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!year || !month || !day) return null;
  return { year, month, day };
}

/**
 * Generate all bucket timestamps for a given time range and bucket type.
 * Used to fill in missing buckets with zero values for continuous chart display.
 */
export function generateBucketTimestamps(
  startTime: Date,
  endTime: Date,
  bucketType: BucketType
): Date[] {
  const timestamps: Date[] = [];
  let current = getBucketStart(startTime, bucketType);
  const end = endTime.getTime();

  while (current.getTime() <= end) {
    timestamps.push(new Date(current));
    current = getNextBucketStart(current, bucketType);
  }

  return timestamps;
}

/**
 * Get the start of the bucket containing the given timestamp.
 */
function getBucketStart(date: Date, bucketType: BucketType): Date {
  const kst = new Date(date.getTime() + KST_OFFSET_MS);

  switch (bucketType) {
    case 'minute': {
      const year = kst.getUTCFullYear();
      const month = kst.getUTCMonth();
      const day = kst.getUTCDate();
      const hour = kst.getUTCHours();
      const minute = kst.getUTCMinutes();
      return new Date(Date.UTC(year, month, day, hour, minute, 0, 0) - KST_OFFSET_MS);
    }
    case 'hour': {
      const year = kst.getUTCFullYear();
      const month = kst.getUTCMonth();
      const day = kst.getUTCDate();
      const hour = kst.getUTCHours();
      return new Date(Date.UTC(year, month, day, hour, 0, 0, 0) - KST_OFFSET_MS);
    }
    case 'day': {
      const year = kst.getUTCFullYear();
      const month = kst.getUTCMonth();
      const day = kst.getUTCDate();
      return new Date(Date.UTC(year, month, day, 0, 0, 0, 0) - KST_OFFSET_MS);
    }
    case 'week': {
      const year = kst.getUTCFullYear();
      const month = kst.getUTCMonth();
      const day = kst.getUTCDate();
      const dayOfWeek = kst.getUTCDay(); // Sunday = 0
      return new Date(Date.UTC(year, month, day - dayOfWeek, 0, 0, 0, 0) - KST_OFFSET_MS);
    }
    case 'month': {
      const year = kst.getUTCFullYear();
      const month = kst.getUTCMonth();
      return new Date(Date.UTC(year, month, 1, 0, 0, 0, 0) - KST_OFFSET_MS);
    }
  }
}

/**
 * Get the start of the next bucket after the given bucket start.
 */
function getNextBucketStart(bucketStart: Date, bucketType: BucketType): Date {
  const kst = new Date(bucketStart.getTime() + KST_OFFSET_MS);
  const year = kst.getUTCFullYear();
  const month = kst.getUTCMonth();
  const day = kst.getUTCDate();
  const hour = kst.getUTCHours();
  const minute = kst.getUTCMinutes();

  switch (bucketType) {
    case 'minute':
      return new Date(Date.UTC(year, month, day, hour, minute + 1, 0, 0) - KST_OFFSET_MS);
    case 'hour':
      return new Date(Date.UTC(year, month, day, hour + 1, 0, 0, 0) - KST_OFFSET_MS);
    case 'day':
      return new Date(Date.UTC(year, month, day + 1, 0, 0, 0, 0) - KST_OFFSET_MS);
    case 'week':
      return new Date(Date.UTC(year, month, day + 7, 0, 0, 0, 0) - KST_OFFSET_MS);
    case 'month':
      return new Date(Date.UTC(year, month + 1, 1, 0, 0, 0, 0) - KST_OFFSET_MS);
  }
}

/**
 * Fill missing buckets with empty data for continuous chart display.
 * Takes existing bucket data and fills gaps with zero values.
 */
export function fillMissingBuckets<T extends { bucket_start: string }>(
  buckets: T[],
  startTime: Date,
  endTime: Date,
  bucketType: BucketType,
  createEmptyBucket: (bucketStart: Date) => T
): T[] {
  const allTimestamps = generateBucketTimestamps(startTime, endTime, bucketType);
  const existingMap = new Map(
    buckets.map((b) => [new Date(b.bucket_start).getTime(), b])
  );

  return allTimestamps.map((timestamp) => {
    const existing = existingMap.get(timestamp.getTime());
    return existing ?? createEmptyBucket(timestamp);
  });
}
