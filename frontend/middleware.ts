import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isAdminRoute = createRouteMatcher(["/admin(.*)"]);
const isAdminLoginRoute = createRouteMatcher(["/admin/login(.*)"]);

export default clerkMiddleware(async (auth, request) => {
  if (isAdminRoute(request) && !isAdminLoginRoute(request)) {
    await auth.protect({
      unauthenticatedUrl: new URL("/admin/login", request.url).toString()
    });
  }
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico)).*)",
    "/(api|trpc)(.*)"
  ]
};
