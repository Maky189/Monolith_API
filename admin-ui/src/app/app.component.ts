import { Component } from '@angular/core';
import { AuthService } from './services/auth.service';
import { LoginComponent } from './pages/login/login.component';
import { ConsoleComponent } from './pages/console/console.component';
import { DevComponent } from './pages/dev/dev.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [LoginComponent, ConsoleComponent, DevComponent],
  template: `
    @if (!auth.token()) {
      <app-login />
    } @else if (auth.role() === 'admin') {
      <app-console />
    } @else {
      <app-dev />
    }
  `
})
export class AppComponent {
  constructor(public auth: AuthService) {}
}
