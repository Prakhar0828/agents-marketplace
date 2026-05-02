import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Marketplace } from "./pages/Marketplace";
import { ChatRoom } from "./pages/ChatRoom";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Marketplace />} />
        <Route path="/hire/:agentId" element={<ChatRoom />} />
      </Routes>
    </BrowserRouter>
  );
}
