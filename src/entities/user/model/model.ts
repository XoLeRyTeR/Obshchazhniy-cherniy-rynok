import type { CatalogItem } from "../../../shared/api";

export type Profile = {
  id: string;
  name: string;
  email: string;
  university: string;
  universityId: string;
  dorm: string;
  dormitoryId: string;
};

export type ApiProfile = {
  id: string;
  name: string;
  email: string;
  university: CatalogItem;
  dormitory: CatalogItem & { university_id: string; };
};

export type AuthResult = { access_token: string; profile: ApiProfile; };

/** Преобразует профиль API в модель интерфейса с названиями и ID вуза и общежития. */
export function mapProfile(data: ApiProfile): Profile {
  return {
    id: data.id,
    name: data.name,
    email: data.email,
    university: data.university.name,
    universityId: data.university.id,
    dorm: data.dormitory.name,
    dormitoryId: data.dormitory.id,
  };
}
export const emptyProfile: Profile = { id: "", name: "", email: "", university: "", universityId: "", dorm: "", dormitoryId: "" };
export const emptySessionState = { signedIn: false, profile: emptyProfile };
