import locations from "./locations.json";

export type Location = {
  name: string;
  url_slug: string;
};

export const LOCATIONS: Location[] = locations as Location[];

export function locationByUrlSlug(slug: string): Location | undefined {
  return LOCATIONS.find((l) => l.url_slug === slug);
}
