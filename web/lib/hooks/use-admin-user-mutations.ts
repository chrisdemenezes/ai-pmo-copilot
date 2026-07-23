import { useMutation, useQueryClient } from "@tanstack/react-query";

import {
  assignRole,
  createUser,
  removeRole,
  setUserActive,
  updateUser,
  type CreateUserInput,
  type UpdateUserInput,
} from "@/lib/domain/user";

/** Every User Management mutation invalidates the same list -- one place
 * to see the invalidation contract instead of it being repeated 5 times. */
function useInvalidateAdminUsers() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["admin-users"] });
}

function useInvalidateAdminUserRoles() {
  const queryClient = useQueryClient();
  return (userId: string) => {
    queryClient.invalidateQueries({ queryKey: ["admin-user-roles", userId] });
    queryClient.invalidateQueries({ queryKey: ["admin-user-roles-index"] });
  };
}

export function useCreateAdminUser() {
  const invalidateUsers = useInvalidateAdminUsers();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateUserInput) => createUser(input),
    onSuccess: () => {
      invalidateUsers();
      // The new user's initial role affects the bulk index too.
      queryClient.invalidateQueries({ queryKey: ["admin-user-roles-index"] });
    },
  });
}

export function useUpdateAdminUser() {
  const invalidate = useInvalidateAdminUsers();
  return useMutation({
    mutationFn: ({ userId, input }: { userId: string; input: UpdateUserInput }) =>
      updateUser(userId, input),
    onSuccess: invalidate,
  });
}

export function useSetAdminUserActive() {
  const invalidate = useInvalidateAdminUsers();
  return useMutation({
    mutationFn: ({ userId, isActive }: { userId: string; isActive: boolean }) =>
      setUserActive(userId, isActive),
    onSuccess: invalidate,
  });
}

export function useAssignAdminUserRole() {
  const invalidateUsers = useInvalidateAdminUsers();
  const invalidateRoles = useInvalidateAdminUserRoles();
  return useMutation({
    mutationFn: ({ userId, roleName }: { userId: string; roleName: string }) =>
      assignRole(userId, roleName),
    onSuccess: (_data, variables) => {
      invalidateUsers();
      invalidateRoles(variables.userId);
    },
  });
}

export function useRemoveAdminUserRole() {
  const invalidateUsers = useInvalidateAdminUsers();
  const invalidateRoles = useInvalidateAdminUserRoles();
  return useMutation({
    mutationFn: ({ userId, roleName }: { userId: string; roleName: string }) =>
      removeRole(userId, roleName),
    onSuccess: (_data, variables) => {
      invalidateUsers();
      invalidateRoles(variables.userId);
    },
  });
}
