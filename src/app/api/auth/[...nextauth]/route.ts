import NextAuth from 'next-auth';
import Credentials from 'next-auth/providers/credentials';
import { redirect } from 'next/navigation';

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Credentials({
      id: 'gatorlink',
      name: 'GatorLink',
      credentials: {
        // We don't need any credentials for this mock provider
      },
      async authorize(credentials) {
        // In a real SAML/Shibboleth flow, you'd verify the assertion here.
        // For this mock, we'll just create a dummy user.
        const user = { 
          id: 'gator-user-123', 
          name: 'Albert Gator', 
          email: 'albert.gator@ufl.edu' 
        };
        
        if (user) {
          return user;
        }
        return null;
      },
    }),
  ],
  callbacks: {
    jwt({ token, user }) {
      if (user) {
        token.id = user.id;
      }
      return token;
    },
    session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
      }
      return session;
    },
  },
  pages: {
    signIn: '/', // Redirect to home page for sign-in
  },
  actions: {
    async signIn({ user, account, profile, email, credentials }) {
      // After successful authentication, redirect to the home page.
      // This prevents the "Unexpected end of JSON input" error.
      redirect('/');
    },
  },
});
