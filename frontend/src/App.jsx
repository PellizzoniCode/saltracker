import { Authenticator } from "@aws-amplify/ui-react";
import { AssetsPage } from "./features/assets/AssetsPage.jsx";

export default function App() {
  return <Authenticator>{({ signOut, user }) => <AssetsPage signOut={signOut} user={user} />}</Authenticator>;
}
